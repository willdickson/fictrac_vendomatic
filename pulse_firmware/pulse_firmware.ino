#include "SerialReceiver.h"

const int TriggerPin = 2;

const int CmdUnspecified = -1;
const int CmdSetTriggerLow = 0;
const int CmdSetTriggerHigh = 1;

SerialReceiver receiver = SerialReceiver();

void setup()
{
    Serial.begin(115200);
    pinMode(TriggerPin,OUTPUT);
    digitalWrite(TriggerPin,LOW);
}

void loop()
{

    int cmd = CmdUnspecified;

    while (Serial.available() > 0) {
        receiver.process(Serial.read());
        if (receiver.messageReady()) {
            cmd = receiver.readInt(0);
            receiver.reset();
            Serial.println(cmd);
        }
    }

    switch (cmd)
    {
        case CmdSetTriggerLow:
            Serial.println("Trigger LOW");
            digitalWrite(TriggerPin,LOW);
            break;

        case CmdSetTriggerHigh:
            Serial.println("Trigger HIGH");
            digitalWrite(TriggerPin,HIGH);
            break;

        default:
            break;

    }
}


