#pragma once
// ESP32 Wi-Fi provisioning for MeshCore LAB. No credentials in firmware.
#include <WiFi.h>
#include <WebServer.h>
#include <DNSServer.h>
#include <Preferences.h>

namespace gateway_wifi {
static WebServer portal(80);
static DNSServer dns;
static Preferences prefs;
static bool ap_active = false;
static bool has_credentials = false;
static unsigned long disconnected_since = 0;
static constexpr unsigned long kFallbackMs = 60000UL;
static const char* kApSsid = "MeshCore-Gateway-Setup";
static const char* kApPassword = "MeshCoreSetup"; // Change before production.

static String htmlEscape(String value) {
  value.replace("&", "&amp;");
  value.replace("<", "&lt;");
  value.replace(">", "&gt;");
  value.replace("\"", "&quot;");
  value.replace("'", "&#39;");
  return value;
}

static void startPortal() {
  if (ap_active) return;
  WiFi.mode(WIFI_AP_STA);
  if (!WiFi.softAP(kApSsid, kApPassword)) {
    Serial.println("[WIFI] Could not start configuration AP");
    return;
  }
  dns.start(53, "*", WiFi.softAPIP());
  portal.on("/", HTTP_GET, []() {
    String page = "<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'></head><body><h2>MeshCore Gateway Wi-Fi</h2><form method='POST' action='/save'><label>SSID <input name='ssid' required maxlength='32'></label><br><label>Password <input type='password' name='pwd' maxlength='63'></label><br><button>Save and connect</button></form><p>Current IP: ";
    page += htmlEscape(WiFi.localIP().toString());
    page += "</p></body></html>";
    portal.send(200, "text/html", page);
  });
  portal.on("/save", HTTP_POST, []() {
    const String ssid = portal.arg("ssid");
    const String pwd = portal.arg("pwd");
    if (ssid.length() == 0 || ssid.length() > 32 || pwd.length() > 63) {
      portal.send(400, "text/plain", "Invalid Wi-Fi credentials");
      return;
    }
    prefs.putString("ssid", ssid);
    prefs.putString("pwd", pwd);
    has_credentials = true;
    portal.send(200, "text/html", "Saved. Gateway connecting; you can close this page.");
    WiFi.begin(ssid.c_str(), pwd.c_str());
    disconnected_since = millis();
    Serial.println("[WIFI] Credentials saved; connecting");
  });
  portal.onNotFound([]() {
    portal.sendHeader("Location", "http://192.168.4.1/", true);
    portal.send(302, "text/plain", "");
  });
  portal.begin();
  ap_active = true;
  Serial.printf("[WIFI] Setup AP %s at %s\n", kApSsid, WiFi.softAPIP().toString().c_str());
}

static void begin() {
  prefs.begin("gateway-wifi", false);
  String ssid = prefs.getString("ssid", "");
  String pwd = prefs.getString("pwd", "");
  has_credentials = ssid.length() > 0;
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  disconnected_since = millis();
  if (has_credentials) {
    WiFi.begin(ssid.c_str(), pwd.c_str());
    Serial.println("[WIFI] Connecting with saved SSID");
  } else {
    Serial.println("[WIFI] No saved SSID; starting configuration portal");
    startPortal();
  }
}

static void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    disconnected_since = 0;
    if (ap_active) {
      portal.stop();
      dns.stop();
      WiFi.softAPdisconnect(true);
      WiFi.mode(WIFI_STA);
      ap_active = false;
      Serial.printf("[WIFI] Connected: %s\n", WiFi.localIP().toString().c_str());
    }
  } else {
    if (!disconnected_since) disconnected_since = millis();
    if (!ap_active && millis() - disconnected_since >= kFallbackMs) {
      Serial.println("[WIFI] Offline 60s; enabling configuration portal");
      startPortal();
    }
  }
  if (ap_active) {
    dns.processNextRequest();
    portal.handleClient();
  }
}
} // namespace gateway_wifi
