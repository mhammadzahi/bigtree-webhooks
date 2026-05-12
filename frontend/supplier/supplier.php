<?php
/**
 * Supplier/Partner Form — WordPress AJAX Proxy
 * Validates Turnstile locally, then proxies to the Python FastAPI backend.
 */

// 1. Expose AJAX URL and Nonce to Frontend
add_action('wp_head', function () {
    ?>
    <script>
        var bt_supplier_vars = {
            ajax_url: "<?php echo esc_url(admin_url('admin-ajax.php')); ?>",
            nonce: "<?php echo wp_create_nonce('bt_supplier_proxy_nonce'); ?>"
        };
    </script>
    <?php
});

// 2. AJAX Handler (logged-in + logged-out users)
add_action('wp_ajax_nopriv_bt_process_supplier_proxy', 'bt_handle_supplier_proxy');
add_action('wp_ajax_bt_process_supplier_proxy', 'bt_handle_supplier_proxy');

function bt_handle_supplier_proxy() {
    // A. Nonce check
    $nonce = isset($_SERVER['HTTP_X_WP_NONCE']) ? sanitize_text_field($_SERVER['HTTP_X_WP_NONCE']) : '';
    if (!wp_verify_nonce($nonce, 'bt_supplier_proxy_nonce')) {
        wp_send_json_error(array('detail' => 'Invalid security token. Please refresh the page.'), 403);
    }

    // B. Parse JSON payload
    $request_body = file_get_contents('php://input');
    $data = json_decode($request_body, true);
    if (empty($data)) {
        wp_send_json_error(array('detail' => 'Invalid request data.'), 400);
    }

    // C. Turnstile validation
    $turnstile_token = isset($data['cf_turnstile_response']) ? sanitize_text_field($data['cf_turnstile_response']) : '';
    if (empty($turnstile_token)) {
        wp_send_json_error(array('detail' => 'Please complete the security verification.'), 400);
    }

    $turnstile_secret = '0x4AAAAAACrUe4EobD9g1r56i19Xr_SfWuM';
    $verify_response = wp_remote_post('https://challenges.cloudflare.com/turnstile/v0/siteverify', array(
        'body' => array(
            'secret'   => $turnstile_secret,
            'response' => $turnstile_token,
            'remoteip' => $_SERVER['REMOTE_ADDR']
        )
    ));

    if (is_wp_error($verify_response)) {
        wp_send_json_error(array('detail' => 'Security service unavailable. Please try again.'), 500);
    }

    $verify_body = json_decode(wp_remote_retrieve_body($verify_response), true);
    if (empty($verify_body['success'])) {
        wp_send_json_error(array('detail' => 'Security check failed. Please refresh and try again.'), 403);
    }

    unset($data['cf_turnstile_response']);

    // D. Forward to Python API
    $api_key      = isset($_SERVER['HTTP_X_API_KEY']) ? sanitize_text_field($_SERVER['HTTP_X_API_KEY']) : '';
    $api_endpoint = 'https://app.bigtree-group.com/bt-supplier-webhook-v1';

    $args = array(
        'method'  => 'POST',
        'headers' => array(
            'Content-Type' => 'application/json',
            'Accept'       => 'application/json',
            'X-API-Key'    => $api_key
        ),
        'body'    => wp_json_encode($data),
        'timeout' => 15
    );

    $python_response = wp_remote_post($api_endpoint, $args);

    if (is_wp_error($python_response)) {
        wp_send_json_error(array('detail' => 'Unable to connect to upstream server.'), 502);
    }

    $response_code = wp_remote_retrieve_response_code($python_response);
    $response_body = json_decode(wp_remote_retrieve_body($python_response), true);

    if ($response_code >= 200 && $response_code < 300) {
        wp_send_json($response_body, $response_code);
    } else {
        wp_send_json_error($response_body, $response_code);
    }
}
