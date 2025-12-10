<?php
/**
 * Snippet Name: AJAX Inquiry Form - User Creation, Auto-Fill & Order Gen
 * Description: Handles backend user creation, auto-login, order generation, and frontend data passing.
 */

// 1. Expose Configuration & User Data to Frontend
add_action('wp_footer', function() {
    $current_user = wp_get_current_user();
    $is_logged_in = is_user_logged_in();
    
    // Prepare User Data if logged in
    $user_data = [];
    if ($is_logged_in) {
        $user_data = array(
            'fname'   => $current_user->first_name ? $current_user->first_name : $current_user->user_login, // fallback
            'lname'   => $current_user->last_name,
            'email'   => $current_user->user_email,
            'phone'   => get_user_meta($current_user->ID, 'billing_phone', true),
            'company' => get_user_meta($current_user->ID, 'billing_company', true),
        );
    }

    $data = array(
        'ajax_url'     => admin_url('admin-ajax.php'),
        'nonce'        => wp_create_nonce('bt_inquiry_process_nonce'), // Updated nonce name
        'is_logged_in' => $is_logged_in ? 'yes' : 'no',
        'user_data'    => $user_data
    );
    ?>
    <script>
        var btAuthObj = <?php echo json_encode($data); ?>;
    </script>
    <?php
});

// 2. AJAX Handler: Process User & Create Order
add_action('wp_ajax_nopriv_bt_process_inquiry_order', 'bt_handle_inquiry_order_process');
add_action('wp_ajax_bt_process_inquiry_order', 'bt_handle_inquiry_order_process');

function bt_handle_inquiry_order_process() {
    // A. Security Check
    check_ajax_referer('bt_inquiry_process_nonce', 'nonce');

    // B. Sanitize Input
    $email   = sanitize_email($_POST['email']);
    $fname   = sanitize_text_field($_POST['fname']);
    $lname   = sanitize_text_field($_POST['lname']);
    $phone   = isset($_POST['phone']) ? sanitize_text_field($_POST['phone']) : '';
    $company = isset($_POST['company']) ? sanitize_text_field($_POST['company']) : '';
    $message = isset($_POST['message']) ? sanitize_textarea_field($_POST['message']) : '';

    // C. User Handling
    $user_id = get_current_user_id();

    if (!$user_id) {
        // User is Guest - Validate & Create
        if (!is_email($email)) {
            wp_send_json_error(array('message' => 'Invalid email address.'));
        }
        if (email_exists($email)) {
            wp_send_json_error(array('message' => 'Email already exists. Please login to submit inquiry.'));
        }

        $password = wp_generate_password(12, true);
        $userdata = array(
            'user_login' => $email,
            'user_email' => $email,
            'user_pass'  => $password,
            'first_name' => $fname,
            'last_name'  => $lname,
            'role'       => 'customer'
        );

        $user_id = wp_insert_user($userdata);
        if (is_wp_error($user_id)) {
            wp_send_json_error(array('message' => $user_id->get_error_message()));
        }

        // Auto-Login
        clean_user_cache($user_id);
        wp_clear_auth_cookie();
        wp_set_current_user($user_id);
        wp_set_auth_cookie($user_id);
    }

    // D. Update Billing Data (For both new and existing users to ensure latest info)
    update_user_meta($user_id, 'billing_first_name', $fname);
    update_user_meta($user_id, 'billing_last_name', $lname);
    update_user_meta($user_id, 'billing_email', $email);
    update_user_meta($user_id, 'billing_phone', $phone);
    update_user_meta($user_id, 'billing_company', $company);

    // E. Create WooCommerce Order
    if (WC()->cart->is_empty()) {
        wp_send_json_error(array('message' => 'Cart is empty.'));
    }

    try {
        $order = wc_create_order();
        
        // Add Products from Cart
        foreach (WC()->cart->get_cart() as $cart_item_key => $values) {
            $order->add_product(
                $values['data'], 
                $values['quantity'],
                array(
                    'variation' => $values['variation'],
                    'totals'    => $values['line_total']
                )
            );
        }

        // Set Billing Address
        $address = array(
            'first_name' => $fname,
            'last_name'  => $lname,
            'company'    => $company,
            'email'      => $email,
            'phone'      => $phone,
            'address_1'  => 'Inquiry via Web Form', // Default placeholder
            'city'       => '',
            'state'      => '',
            'postcode'   => '',
            'country'    => ''
        );
        $order->set_address($address, 'billing');

        // Add Customer Note
        if (!empty($message)) {
            $order->add_order_note('Customer Message: ' . $message, true);
        }

        // Assign to User
        $order->set_customer_id($user_id);
        
        // Calculate Totals
        $order->calculate_totals();

        // Set Status (e.g., On Hold or Processing)
        $order->update_status('on-hold', 'Inquiry Order Created via Popup');

        // F. Empty Cart
        WC()->cart->empty_cart();

        wp_send_json_success(array(
            'message'  => 'Order created successfully.',
            'redirect' => '/my-account/orders/' // Redirect destination
        ));

    } catch (Exception $e) {
        wp_send_json_error(array('message' => 'Order creation failed: ' . $e->getMessage()));
    }
}