package com.layali.riyadh;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

public class MainActivity extends Activity {
    private WebView webView;
    private PermissionRequest pendingRequest;
    private static final int MEDIA_PERMISSION_REQUEST = 71;

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        webView = new WebView(this);
        setContentView(webView);
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        s.setJavaScriptCanOpenWindowsAutomatically(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        webView.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) { return false; }
        });
        webView.setWebChromeClient(new WebChromeClient() {
            @Override public void onPermissionRequest(PermissionRequest request) {
                boolean cam = false, mic = false;
                for (String x : request.getResources()) {
                    if (PermissionRequest.RESOURCE_VIDEO_CAPTURE.equals(x)) cam = true;
                    if (PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(x)) mic = true;
                }
                boolean okCam = !cam || checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED;
                boolean okMic = !mic || checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED;
                if (okCam && okMic) request.grant(request.getResources());
                else {
                    pendingRequest = request;
                    String[] p = cam && mic
                        ? new String[]{Manifest.permission.CAMERA, Manifest.permission.RECORD_AUDIO}
                        : cam ? new String[]{Manifest.permission.CAMERA} : new String[]{Manifest.permission.RECORD_AUDIO};
                    requestPermissions(p, MEDIA_PERMISSION_REQUEST);
                }
            }
            @Override public void onPermissionRequestCanceled(PermissionRequest request) {
                if (pendingRequest == request) pendingRequest = null;
            }
        });
        if (savedInstanceState == null) webView.loadUrl("file:///android_asset/مكتبة_الألعاب-1.html");
        else webView.restoreState(savedInstanceState);
    }

    @Override public void onRequestPermissionsResult(int code, String[] p, int[] results) {
        super.onRequestPermissionsResult(code, p, results);
        if (code == MEDIA_PERMISSION_REQUEST && pendingRequest != null) {
            boolean granted = results.length > 0;
            for (int x : results) if (x != PackageManager.PERMISSION_GRANTED) granted = false;
            if (granted) pendingRequest.grant(pendingRequest.getResources());
            else {
                pendingRequest.deny();
                Toast.makeText(this, "يلزم السماح بالإذن لاستخدام هذه الميزة", Toast.LENGTH_SHORT).show();
            }
            pendingRequest = null;
        }
    }
    @Override protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        webView.saveState(out);
    }
    @Override public void onBackPressed() {
        if (webView != null && webView.canGoBack()) webView.goBack(); else super.onBackPressed();
    }
    @Override protected void onDestroy() {
        if (webView != null) { webView.destroy(); webView = null; }
        super.onDestroy();
    }
}
