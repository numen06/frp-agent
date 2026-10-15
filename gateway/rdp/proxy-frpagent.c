/* FreeRDP performs RDP termination; the application authenticates and routes. */
#include <freerdp/server/proxy/proxy_modules_api.h>
#include <freerdp/server/proxy/proxy_context.h>
#include <freerdp/settings.h>
#include <winpr/synch.h>
#include <curl/curl.h>
#include <json-c/json.h>
#include <openssl/pem.h>
#include <openssl/x509.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <stdlib.h>
#include <string.h>

static const char* NAME = "frpagent";
typedef struct { char data[16385]; size_t length; } responseBuffer;

static size_t receive_body(char* ptr, size_t size, size_t count, void* arg)
{
    responseBuffer* buffer = arg;
    if (size && count > (16384 - buffer->length) / size) return 0;
    size_t length = size * count;
    memcpy(buffer->data + buffer->length, ptr, length);
    buffer->length += length;
    buffer->data[buffer->length] = 0;
    return length;
}

static const char* field(json_object* value, const char* name)
{
    json_object* item = NULL;
    if (!json_object_object_get_ex(value, name, &item) ||
        !json_object_is_type(item, json_type_string)) return NULL;
    return json_object_get_string(item);
}

static json_object* target(proxyPlugin* plugin, proxyData* data)
{
    json_object* state = plugin->mgr->GetPluginData(plugin->mgr, NAME, data);
    json_object* result = NULL;
    if (state) json_object_object_get_ex(state, "target", &result);
    return result;
}

static int connection_port(proxyPlugin* plugin, proxyData* data)
{
    json_object* state = plugin->mgr->GetPluginData(plugin->mgr, NAME, data);
    json_object* port = NULL;
    if (state) json_object_object_get_ex(state, "connection_port", &port);
    return port ? json_object_get_int(port) : 0;
}

static BOOL fetch_target(proxyPlugin* plugin, proxyData* data, void* arg)
{
    proxyFetchTargetEventInfo* event = arg;
    rdpSettings* settings = data->ps->context.settings;
    const char* username = freerdp_settings_get_string(settings, FreeRDP_Username);
    const char* password = freerdp_settings_get_string(settings, FreeRDP_Password);
    const char* endpoint = getenv("FRP_RDP_AUTH_URL");
    const char* secret = getenv("FRP_RDP_INTERNAL_SECRET");
    int source_port = connection_port(plugin, data);
    if (!username || !password || !endpoint || !secret ||
        strncmp(endpoint, "http://127.0.0.1:", 17) != 0 ||
        source_port < 1) return FALSE;
    json_object* request = json_object_new_object();
    json_object_object_add(request, "username", json_object_new_string(username));
    json_object_object_add(request, "password", json_object_new_string(password));
    json_object_object_add(request, "connection_port", json_object_new_int(source_port));
    char header[256];
    if (strlen(secret) > 128 || snprintf(header, sizeof(header), "X-Rdp-Internal-Secret: %s", secret) < 0) {
        json_object_put(request); return FALSE;
    }
    CURL* client = curl_easy_init();
    struct curl_slist* headers = NULL;
    headers = curl_slist_append(headers, "Content-Type: application/json");
    headers = curl_slist_append(headers, header);
    responseBuffer response = {0}; long status = 0; BOOL ok = FALSE;
    if (!client || !headers) goto cleanup;
    curl_easy_setopt(client, CURLOPT_URL, endpoint);
    curl_easy_setopt(client, CURLOPT_PROXY, "");
    curl_easy_setopt(client, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(client, CURLOPT_POSTFIELDS, json_object_to_json_string_ext(request, JSON_C_TO_STRING_PLAIN));
    curl_easy_setopt(client, CURLOPT_WRITEFUNCTION, receive_body);
    curl_easy_setopt(client, CURLOPT_WRITEDATA, &response);
    curl_easy_setopt(client, CURLOPT_TIMEOUT_MS, 5000L);
    curl_easy_setopt(client, CURLOPT_CONNECTTIMEOUT_MS, 1000L);
    curl_easy_setopt(client, CURLOPT_NOSIGNAL, 1L);
    if (curl_easy_perform(client) != CURLE_OK) goto cleanup;
    curl_easy_getinfo(client, CURLINFO_RESPONSE_CODE, &status);
    if (status != 200) goto cleanup;
    json_object* result = json_tokener_parse(response.data);
    json_object* port = NULL;
    if (!result) goto cleanup;
    const char* host = field(result, "address");
    const char* pin = field(result, "fingerprint");
    if (!host || !pin || strlen(pin) != 64 || !field(result, "username") ||
        !field(result, "password") || !field(result, "domain") ||
        !json_object_object_get_ex(result, "port", &port) ||
        json_object_get_int(port) < 1 || json_object_get_int(port) > 65535) {
        json_object_put(result); goto cleanup;
    }
    event->target_address = strdup(host);
    event->target_port = json_object_get_int(port);
    event->fetch_method = PROXY_FETCH_TARGET_USE_CUSTOM_ADDR;
    json_object* state = plugin->mgr->GetPluginData(plugin->mgr, NAME, data);
    if (!event->target_address || !state) {
        free(event->target_address); event->target_address = NULL;
        json_object_put(result); goto cleanup;
    }
    json_object_object_add(state, "target", result);
    /* The copied client settings are overwritten before the upstream is opened. */
    freerdp_settings_set_string(settings, FreeRDP_Password, NULL);
    ok = TRUE;
cleanup:
    if (client) curl_easy_cleanup(client);
    curl_slist_free_all(headers);
    json_object_put(request);
    OPENSSL_cleanse(response.data, sizeof(response.data));
    return ok;
}

static BOOL connect_target(proxyPlugin* plugin, proxyData* data, void* arg)
{
    json_object* result = target(plugin, data);
    rdpSettings* settings = data->pc->context.settings;
    if (!result) return FALSE;
    BOOL ok = freerdp_settings_set_string(settings, FreeRDP_Username, field(result, "username")) &&
        freerdp_settings_set_string(settings, FreeRDP_Password, field(result, "password")) &&
        freerdp_settings_set_string(settings, FreeRDP_Domain, field(result, "domain")) &&
        freerdp_settings_set_bool(settings, FreeRDP_NlaSecurity, TRUE) &&
        freerdp_settings_set_bool(settings, FreeRDP_TlsSecurity, FALSE) &&
        freerdp_settings_set_bool(settings, FreeRDP_RdpSecurity, FALSE) &&
        freerdp_settings_set_uint16(settings, FreeRDP_TLSMinVersion, 0x0303) &&
        freerdp_settings_set_bool(settings, FreeRDP_AutoReconnectionEnabled, FALSE);
    json_object_object_del(result, "password");
    return ok;
}

static BOOL report_connected(proxyPlugin* plugin, proxyData* data, void* arg)
{
    int source_port = connection_port(plugin, data);
    const char* endpoint = getenv("FRP_RDP_AUTH_URL");
    const char* secret = getenv("FRP_RDP_INTERNAL_SECRET");
    if (!endpoint || !secret || strlen(secret) > 128 ||
        strncmp(endpoint, "http://127.0.0.1:", 17) != 0 || source_port < 1) return FALSE;
    char body[128], header[256];
    snprintf(body, sizeof(body), "{\"connection_port\":%d,\"phase\":\"connected\"}", source_port);
    snprintf(header, sizeof(header), "X-Rdp-Internal-Secret: %s", secret);
    CURL* client = curl_easy_init(); if (!client) return FALSE;
    struct curl_slist* headers = curl_slist_append(NULL, "Content-Type: application/json");
    headers = curl_slist_append(headers, header);
    responseBuffer response = {0}; long status = 0;
    curl_easy_setopt(client, CURLOPT_URL, endpoint);
    curl_easy_setopt(client, CURLOPT_PROXY, "");
    curl_easy_setopt(client, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(client, CURLOPT_POSTFIELDS, body);
    curl_easy_setopt(client, CURLOPT_WRITEFUNCTION, receive_body);
    curl_easy_setopt(client, CURLOPT_WRITEDATA, &response);
    curl_easy_setopt(client, CURLOPT_TIMEOUT_MS, 5000L);
    curl_easy_setopt(client, CURLOPT_NOSIGNAL, 1L);
    CURLcode rc = curl_easy_perform(client);
    curl_easy_getinfo(client, CURLINFO_RESPONSE_CODE, &status);
    curl_slist_free_all(headers); curl_easy_cleanup(client);
    return rc == CURLE_OK && status == 200;
}

static BOOL verify_target(proxyPlugin* plugin, proxyData* data, void* arg)
{
    json_object* result = target(plugin, data);
    if (!result) return FALSE;
    const char* expected = field(result, "fingerprint");
    pClientContext* pc = data->pc;
    BIO* bio = BIO_new_mem_buf(Stream_Buffer(pc->remote_pem), Stream_Length(pc->remote_pem));
    X509* cert = bio ? PEM_read_bio_X509(bio, NULL, NULL, NULL) : NULL;
    unsigned char digest[EVP_MAX_MD_SIZE]; unsigned int length = 0; char actual[65];
    BOOL ok = FALSE;
    if (cert && expected && X509_digest(cert, EVP_sha256(), digest, &length) && length == 32) {
        for (size_t i = 0; i < 32; i++) snprintf(actual + i * 2, 3, "%02x", digest[i]);
        ok = CRYPTO_memcmp(expected, actual, 64) == 0;
    }
    X509_free(cert); BIO_free(bio); return ok;
}

static BOOL release_state(proxyPlugin* plugin, proxyData* data, void* arg)
{
    json_object* result = plugin->mgr->GetPluginData(plugin->mgr, NAME, data);
    if (result) json_object_put(result);
    return TRUE;
}

static BOOL session_end(proxyPlugin* plugin, proxyData* data, void* arg)
{
    /* An upstream thread owns the state until all certificate/auth callbacks finish. */
    return data->client_thread ? TRUE : release_state(plugin, data, arg);
}

static BOOL reject_redirect(proxyPlugin* plugin, proxyData* data, void* arg) { return FALSE; }
static BOOL initialize(proxyPlugin* plugin, proxyData* data, void* arg)
{
    /* FreeRDP transfers peer->sockfd to its file-descriptor event at context creation. */
    struct sockaddr_in peer = {0}; socklen_t size = sizeof(peer);
    freerdp_peer* client = data->ps->context.peer;
    int fd = GetEventFileDescriptor(client->GetEventHandle(client));
    if (fd < 0 || getpeername(fd, (struct sockaddr*)&peer, &size) ||
        peer.sin_family != AF_INET || ntohl(peer.sin_addr.s_addr) != INADDR_LOOPBACK ||
        !freerdp_settings_set_uint16(data->ps->context.settings, FreeRDP_TLSMinVersion, 0x0303)) return FALSE;
    json_object* state = json_object_new_object();
    if (!state) return FALSE;
    json_object_object_add(state, "connection_port", json_object_new_int(ntohs(peer.sin_port)));
    if (!plugin->mgr->SetPluginData(plugin->mgr, NAME, data, state)) {
        json_object_put(state); return FALSE;
    }
    return TRUE;
}

FREERDP_API BOOL proxy_module_entry_point(proxyPluginsManager* manager, void* userdata)
{
    if (curl_global_init(CURL_GLOBAL_DEFAULT) != CURLE_OK) return FALSE;
    proxyPlugin plugin = {0};
    plugin.name = NAME; plugin.description = "frp-agent platform authentication and credential mapping";
    plugin.ServerSessionInitialize = initialize;
    plugin.ServerFetchTargetAddr = fetch_target;
    plugin.ClientInitConnect = connect_target;
    plugin.ClientUninitConnect = release_state;
    plugin.ClientPostConnect = report_connected;
    plugin.ClientX509Certificate = verify_target;
    plugin.ClientRedirect = reject_redirect;
    plugin.ServerSessionEnd = session_end;
    return manager->RegisterPlugin(manager, &plugin);
}
