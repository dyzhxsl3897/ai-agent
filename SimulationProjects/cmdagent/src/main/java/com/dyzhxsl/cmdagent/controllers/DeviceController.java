package com.dyzhxsl.cmdagent.controllers;

import com.dyzhxsl.cmdagent.services.DeviceStateService;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
@CrossOrigin
public class DeviceController {

    private final DeviceStateService service;

    public DeviceController(DeviceStateService service) {
        this.service = service;
    }

    // ---- Light ----

    @GetMapping(value = "/light/on", produces = MediaType.TEXT_PLAIN_VALUE)
    public String lightOn() {
        service.turnLightOn();
        return "OK";
    }

    @GetMapping(value = "/light/off", produces = MediaType.TEXT_PLAIN_VALUE)
    public String lightOff() {
        service.turnLightOff();
        return "OK";
    }

    // return true/false indicating the light is on or off
    @GetMapping(value = "/light/status", produces = MediaType.APPLICATION_JSON_VALUE)
    public boolean lightStatus() {
        return service.isLightOn();
    }

    // ---- Garage Door ----

    @GetMapping(value = "/garagedoor/open", produces = MediaType.TEXT_PLAIN_VALUE)
    public String garageOpen() {
        service.openGarageDoor();

        return "OK";
    }

    @GetMapping(value = "/garagedoor/close", produces = MediaType.TEXT_PLAIN_VALUE)
    public String garageClose() {
        service.closeGarageDoor();
        return "OK";
    }

    // return a number 0..100 indicating door height
    @GetMapping(value = "/garagedoor/status", produces = MediaType.APPLICATION_JSON_VALUE)
    public int garageStatus() {
        return service.getGarageDoorHeight();
    }
}
