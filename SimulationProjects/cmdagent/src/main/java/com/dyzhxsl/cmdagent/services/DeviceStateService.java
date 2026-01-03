package com.dyzhxsl.cmdagent.services;

import org.springframework.stereotype.Service;

import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

@Service
public class DeviceStateService {
    // Light: on/off
    private final AtomicBoolean lightOn = new AtomicBoolean(false);

    private final AtomicBoolean garageDoorMoving = new AtomicBoolean(false);

    // Garage door height: 0..100
    private final AtomicInteger garageDoorHeight = new AtomicInteger(0);

    public boolean isLightOn() {
        return lightOn.get();
    }

    public void turnLightOn() {
        lightOn.set(true);
    }

    public void turnLightOff() {
        lightOn.set(false);
    }

    public int getGarageDoorHeight() {
        return garageDoorHeight.get();
    }

    public void openGarageDoor() {
        garageDoorHeight.set(100);
    }

    public void closeGarageDoor() {
        garageDoorHeight.set(0);
    }

    public AtomicBoolean getGarageDoorMoving() {
        return garageDoorMoving;
    }
}
