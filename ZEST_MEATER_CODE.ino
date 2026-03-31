#include <cstdlib>
#include <string.h>
#include <time.h>
#include <ModbusMaster.h>
#include <esp_task_wdt.h>

#include <WiFi.h>
#include <mqtt_client.h>

#include <az_iot_hub_client.h>
#include <az_result.h>
#include <az_span.h>
#include <ArduinoJson.h>
#include "AzIoTSasToken.h"
#include "SerialLogger.h"
#include "ca.h"
#include "iot_configs.h"

#define sizeofarray(a) (sizeof(a) / sizeof(a[0]))
#define NTP_SERVERS "pool.ntp.org", "time.nist.gov"
#define MQTT_QOS1 1
#define DO_NOT_RETAIN_MSG 0
#define SAS_TOKEN_DURATION_IN_MINUTES 60
#define UNIX_TIME_NOV_13_2017 1510592825

#define PST_TIME_ZONE -8
#define PST_TIME_ZONE_DST_DIFF   1

#define GMT_OFFSET_SECS (PST_TIME_ZONE * 3600)
#define GMT_OFFSET_SECS_DST ((PST_TIME_ZONE + PST_TIME_ZONE_DST_DIFF) * 3600)

#define WDT_TIMEOUT_SECONDS 60  // Watchdog timeout in seconds


static const char* ssid = IOT_CONFIG_WIFI_SSID;
static const char* password = IOT_CONFIG_WIFI_PASSWORD;
static const char* host = IOT_CONFIG_IOTHUB_FQDN;
static const char* mqtt_broker_uri = "mqtts://" IOT_CONFIG_IOTHUB_FQDN;
static const char* device_id = IOT_CONFIG_DEVICE_ID;
static const int mqtt_port = 8883;

static esp_mqtt_client_handle_t mqtt_client;
static az_iot_hub_client client;

static char mqtt_client_id[128];
static char mqtt_username[128];
static char mqtt_password[200];
static uint8_t sas_signature_buffer[256];
static unsigned long next_telemetry_send_time_ms = 0;
static char telemetry_topic[128];
static uint8_t telemetry_payload[100];
static uint32_t telemetry_send_count = 0;
static DynamicJsonDocument docb(200);
char timestamp[20]; 

String timestampcloud = "";

static AzIoTSasToken sasToken(
    &client,
    AZ_SPAN_FROM_STR(IOT_CONFIG_DEVICE_KEY),
    AZ_SPAN_FROM_BUFFER(sas_signature_buffer),
    AZ_SPAN_FROM_BUFFER(mqtt_password));

static void connectToWiFi()
{
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Logger.Info("WiFi connected, IP address: " + WiFi.localIP().toString());
  Serial.print("WiFi SSID: ");
  Serial.println(WiFi.SSID());
}

#define RXD2 16
#define TXD2 17 
uint8_t result;
#define RED 25
#define GREEN 26
#define BLUE 27



double totaliser = 0;


int Post_Data_on_UART(int slave_id) {

  ModbusMaster node;
  node.begin(slave_id, Serial2);

  const int maxRetries = 3;     // number of retries
  int attempt = 0;
  uint8_t result = 0;

  digitalWrite(GREEN, LOW);

  // -------------------------------------------------------------------
  // 🔄 Retry Loop
  // -------------------------------------------------------------------
  while (attempt < maxRetries) {

    Serial.print("Attempt ");
    Serial.print(attempt + 1);
    Serial.println(" of 3");

    result = node.readHoldingRegisters(0x0052, 12);

    if (result == node.ku8MBSuccess) {
      Serial.println("Modbus Read Success");
      break;   // exit retry loop
    }

    Serial.print("Failed, Error code: ");
    Serial.println(result);

    attempt++;
    delay(200); // small delay before retry
  }

  // If all 3 attempts failed
  if (result != node.ku8MBSuccess) {
    Serial.println("All retries failed.");
    digitalWrite(GREEN, HIGH);
    return 0;
  }

  // -------------------------------------------------------------------
  // ✔ SUCCESS : Process Registers Below
  // -------------------------------------------------------------------
  
  float totdecimalfloat = 0.0;
  long tot = 0;

  uint32_t totdecimalhex = (node.getResponseBuffer(0x0A) << 16) |
                            node.getResponseBuffer(0x0B);

  uint32_t tothex = (node.getResponseBuffer(0x08) << 16) |
                     node.getResponseBuffer(0x09);

  totdecimalfloat = *((float*)&totdecimalhex);
  tot = *((long*)&tothex);

  Serial.println(node.getResponseBuffer(0x0A), HEX); delay(10);
  Serial.println(node.getResponseBuffer(0x0B), HEX); delay(10);

  Serial.println("data collected    new");
  Serial.println(totdecimalhex, HEX);
  Serial.println(tot);

  totaliser = (float)tot + totdecimalfloat;

  Serial.print("Slave ID:");
  Serial.println(slave_id);
  Serial.println(totaliser);

  digitalWrite(GREEN, HIGH);
  return 1;
}
int Post_Data_on_UART2(int slave_id) {

  ModbusMaster node;
  
  node.begin(slave_id, Serial2);

    result = node.readHoldingRegisters(0X005A, 4);
  Serial.println(result);
  if (result == node.ku8MBSuccess)
  {


  //float flowratefloat= 0.0;
  //unsigned long totdecimallong = 0;  
  //long tot = 0;
  
  Serial.println("\nBuffer Start");
  for(int i = 0; i< 4 ; i++)
  {
    Serial.println(node.getResponseBuffer(i),HEX); 
  }
  Serial.println("Buffer End\n");

   //uint32_t flowratehex = (node.getResponseBuffer(0x00)<<16)| node.getResponseBuffer(0x01);
   unsigned long totdecimallong = (node.getResponseBuffer(0x01)<<16)|node.getResponseBuffer(0x00);
   uint32_t tothex = (node.getResponseBuffer(0x03)<<16)|node.getResponseBuffer(0x02);
   //flowratefloat = *((float*)&flowratehex);
   float totdecimalfloat = *((float*)&tothex);
   Serial.print("Data int = ");
   Serial.println(totdecimallong);
   Serial.print("Data dec = ");
   Serial.println(totdecimalfloat);
   totaliser =  totdecimallong;
    Serial.print("Before multiplier");
    Serial.println(totaliser);
    return(1);
  }
  else
  {
    Serial.println("RS485 fail");
    return(0);
  }
}
int Post_Data_on_UART1(int slave_id) {

  ModbusMaster node;

  digitalWrite(GREEN, LOW);

    node.begin(slave_id, Serial2);

    result = node.readInputRegisters(0x1010, 12);
  Serial.println(result);
  if (result == node.ku8MBSuccess)
  {
    float totdecimalfloat = 0.0;  
    long tot = 0;
    uint32_t totdecimalhex = (node.getResponseBuffer(0x0A)<<16)|node.getResponseBuffer(0x0B);
    uint32_t tothex = (node.getResponseBuffer(0x08)<<16)|node.getResponseBuffer(0x09);
    totdecimalfloat = *((float*)&totdecimalhex);
    tot = *((long*)&tothex);
    Serial.println(node.getResponseBuffer(0x0A),HEX);delay(10);
    Serial.println(node.getResponseBuffer(0x0B),HEX);delay(10); 
    Serial.println("data collected    new    ");
    Serial.println(totdecimalhex,HEX);
    Serial.println(tot);
    totaliser =  (float)tot + totdecimalfloat ;
    Serial.print("Slave ID:");
    Serial.println(slave_id);
    Serial.println(totaliser);
    digitalWrite(GREEN, HIGH);
    return(1);
  }
  Serial.println("Reading failed");
  digitalWrite(GREEN, HIGH);
  return(0); 
 }

static void initializeTime()
{
  Logger.Info("Setting time using SNTP");

  configTime(GMT_OFFSET_SECS, GMT_OFFSET_SECS_DST, NTP_SERVERS);
  time_t now = time(NULL);
  while (now < UNIX_TIME_NOV_13_2017)
  {
    delay(500);
    Serial.print(".");
    now = time(nullptr);
  }
  Serial.println("");
  Logger.Info("Time initialized!");
}

void receivedCallback(char* topic, byte* payload, unsigned int length)
{
  Logger.Info("Received [");
  Logger.Info(topic);
  Logger.Info("]: ");
  for (int i = 0; i < length; i++)
  {
    Serial.print((char)payload[i]);
  }
}

static esp_err_t mqtt_event_handler(esp_mqtt_event_handle_t event)
{
  switch (event->event_id)
  {
    case MQTT_EVENT_ERROR:
      Logger.Info("MQTT event MQTT_EVENT_ERROR");
      break;
    case MQTT_EVENT_CONNECTED:
      Logger.Info("MQTT event MQTT_EVENT_CONNECTED");
      break;
    case MQTT_EVENT_DISCONNECTED:
      Logger.Info("MQTT event MQTT_EVENT_DISCONNECTED");
      break;
    case MQTT_EVENT_SUBSCRIBED:
      Logger.Info("MQTT event MQTT_EVENT_SUBSCRIBED");
      break;
    case MQTT_EVENT_UNSUBSCRIBED:
      Logger.Info("MQTT event MQTT_EVENT_UNSUBSCRIBED");
      break;
    case MQTT_EVENT_PUBLISHED:
      Logger.Info("MQTT event MQTT_EVENT_PUBLISHED");
      break;
    case MQTT_EVENT_DATA:
      Logger.Info("MQTT event MQTT_EVENT_DATA");
      break;
    case MQTT_EVENT_BEFORE_CONNECT:
      Logger.Info("MQTT event MQTT_EVENT_BEFORE_CONNECT");
      break;
    default:
      Logger.Error("MQTT event UNKNOWN");
      break;
  }
}

static void initializeIoTHubClient()
{
  if (az_result_failed(az_iot_hub_client_init(
          &client,
          az_span_create((uint8_t*)host, strlen(host)),
          az_span_create((uint8_t*)device_id, strlen(device_id)),
          NULL)))
  {
    Logger.Error("Failed initializing Azure IoT Hub client");
    return;
  }

  size_t client_id_length;
  if (az_result_failed(az_iot_hub_client_get_client_id(
          &client, mqtt_client_id, sizeof(mqtt_client_id) - 1, &client_id_length)))
  {
    Logger.Error("Failed getting client id");
    return;
  }

  // Get the MQTT user name used to connect to IoT Hub
  if (az_result_failed(az_iot_hub_client_get_user_name(
          &client, mqtt_username, sizeofarray(mqtt_username), NULL)))
  {
    Logger.Error("Failed to get MQTT clientId, return code");
    return;
  }

  Logger.Info("Client ID: " + String(mqtt_client_id));
  Logger.Info("Username: " + String(mqtt_username));
}

static int initializeMqttClient()
{
  if (sasToken.Generate(SAS_TOKEN_DURATION_IN_MINUTES) != 0)
  {
    Logger.Error("Failed generating SAS token");
    return 1;
  }

  esp_mqtt_client_config_t mqtt_config;
  memset(&mqtt_config, 0, sizeof(mqtt_config));
  mqtt_config.uri = mqtt_broker_uri;
  mqtt_config.port = mqtt_port;
  mqtt_config.client_id = mqtt_client_id;
  mqtt_config.username = mqtt_username;
  mqtt_config.password = (const char*)az_span_ptr(sasToken.Get());
  mqtt_config.keepalive = 30;
  mqtt_config.disable_clean_session = 0;
  mqtt_config.disable_auto_reconnect = false;
  mqtt_config.event_handle = mqtt_event_handler;
  mqtt_config.user_context = NULL;
  mqtt_config.cert_pem = (const char*)ca_pem;

  mqtt_client = esp_mqtt_client_init(&mqtt_config);

  if (mqtt_client == NULL)
  {
    Logger.Error("Failed creating mqtt client");
    return 1;
  }

  esp_err_t start_result = esp_mqtt_client_start(mqtt_client);

  if (start_result != ESP_OK)
  {
    Logger.Error("Could not start mqtt client; error code:" + start_result);
    return 1;
  }
  else
  {
    Logger.Info("MQTT client started");
    return 0;
  }
}

static uint32_t getEpochTimeInSecs() 
{ 
  return (uint32_t)time(NULL);
}

static int establishConnection()
{
  connectToWiFi();
  initializeTime();
  initializeIoTHubClient();
  (void)initializeMqttClient();
}


void getcreated_on()
{
    time_t     created_now;
    struct tm  ts;
    char       buf[80];

    // Get current time
    time(&created_now);

    // Format time, "ddd yyyy-mm-dd hh:mm:ss zzz"
    ts = *gmtime(&created_now);
    strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &ts);
    timestampcloud = (char*)buf;

  // sprintf (timestamp, "%4d-%02d-%02d %02d:%02d:%02d", year(), month(),day(), hour(), minute(), second());
  Logger.Info(timestampcloud);

}

static char *getTelemetryPayload(int sid)
{
  az_span temp_span = az_span_create(telemetry_payload, sizeof(telemetry_payload));
  getcreated_on();
  docb.clear();  
  if(sid==1) docb["unit_id"] = "FG27190F";
  else if(sid==2) docb["unit_id"] = "FG27191F";
  else if(sid==3) docb["unit_id"] = "FG27192F";
  else if(sid==4) docb["unit_id"] = "FG27193F";
  docb["consumption"] = String(totaliser);
  docb["created_on"] = timestampcloud;
  
  serializeJson(docb, telemetry_payload, sizeof(telemetry_payload));
  serializeJson(docb, Serial);
  
  return (char *)telemetry_payload;
}

static void sendTelemetry(int sid)
{
  digitalWrite(BLUE, LOW);
  az_span telemetry = AZ_SPAN_FROM_BUFFER(telemetry_payload);

  Logger.Info("Sending telemetry ...");

  // The topic could be obtained just once during setup,
  // however if properties are used the topic need to be generated again to reflect the
  // current values of the properties.
  if (az_result_failed(az_iot_hub_client_telemetry_get_publish_topic(
          &client, NULL, telemetry_topic, sizeof(telemetry_topic), NULL)))
  {
    Logger.Error("Failed az_iot_hub_client_telemetry_get_publish_topic");
    return;
  }
  strcat(telemetry_topic,"$.ct=application%2Fjson&$.ce=utf-8");
  
  const char *payload_ptr = getTelemetryPayload(sid);

  if (esp_mqtt_client_publish(
          mqtt_client,
          telemetry_topic,
          payload_ptr,
          strlen(payload_ptr),
          MQTT_QOS1,
          DO_NOT_RETAIN_MSG)
      == 0)
  {
    Logger.Error("Failed publishing");
  }
  else
  {
    Logger.Info("Message published successfully");
  }
  digitalWrite(BLUE, HIGH);
}



void setup() {
  // put your setup code here, to run once:

  Serial2.begin(9600);
  Serial.print("MAC ID: ");
  Serial.println(WiFi.macAddress());

  // Initialize Watchdog Timer with 60 second timeout
  esp_task_wdt_init(WDT_TIMEOUT_SECONDS, true);  // true = enable panic (reset on timeout)
  esp_task_wdt_add(NULL);  // Add current task (loop) to watchdog
  Logger.Info("Watchdog Timer initialized with 60 second timeout");

  establishConnection();
}

void loop() {

  // Reset watchdog timer to prevent reset during normal operation
  esp_task_wdt_reset();

  // put your main code here, to run repeatedly:

  if (WiFi.status() != WL_CONNECTED)
  {
    connectToWiFi();
  }
  else if (sasToken.IsExpired())
  {
    Logger.Info("SAS token expired; reconnecting with a new one.");
    (void)esp_mqtt_client_destroy(mqtt_client);
    initializeMqttClient();
  }
  else if (millis() > next_telemetry_send_time_ms)
  {
    totaliser=0;
    if(Post_Data_on_UART(1))
      sendTelemetry(1);
    delay(500);
    if(Post_Data_on_UART2(1))
      sendTelemetry(1);
    delay(500);
    if(Post_Data_on_UART1(2))
      sendTelemetry(2);
    delay(500);
if(Post_Data_on_UART1(3))
      sendTelemetry(3); 
    delay(500);
    if(Post_Data_on_UART1(4))
      sendTelemetry(4);
    delay(500);
    
       next_telemetry_send_time_ms = millis() + TELEMETRY_FREQUENCY_MILLISECS;
  }
}
