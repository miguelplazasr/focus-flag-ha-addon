# FocusFlag Home Assistant Add-on

Control a Luxafor Flag USB light automatically based on your Webex meeting status using this Home Assistant add-on.

## 📊 Description
This add-on integrates with Webex to monitor your current meeting status and toggle a Luxafor Flag accordingly:

- 🔴 Red light when you're in a meeting
- ⚪️ Off when you're not

Manual control is also available via a toggle in the Home Assistant dashboard.


## ⚙️ Features
- Automatically polls Webex API for meeting presence
- USB control of Luxafor Flag (via PyUSB and pyluxafor)
- Manual override through Home Assistant input_boolean
- Configurable polling interval and working hours


## 🔧 Installation
1. Copy the add-on into your local add-ons folder: `/addons/local/focus_flag_ha_addon`
2. Inside Home Assistant, go to **Settings** > **Add-ons** > **Add-on Store** > Three-dot menu > **Repositories**
3. Add your GitHub repo URL (if published)
4. Install and start the add-on


## ⚙️ Configuration
In the add-on configuration panel, set the following options:

```yaml
webex_enabled: true
webex_token: "YOUR_WEBEX_ACCESS_TOKEN"
webex_endpoint: "https://webex-api.example.com/status"
webex_interval: 60  # in seconds
work_hours:
  start: "08:00"
  end: "17:00"
```

To enable manual override, create an `input_boolean` in your Home Assistant `configuration.yaml`:

```yaml
input_boolean:
  focus_flag_switch:
    name: FocusFlag Manual Toggle
    initial: off
    icon: mdi:toggle-switch
```

Then create a simple automation to call the REST API exposed by this add-on.


## 📆 Usage
- The add-on polls Webex every N seconds.
- If you're in a meeting **within work hours**, the Luxafor light turns red.
- If you're not in a meeting, the light turns off.
- If manual toggle is ON, Webex automation is ignored.


## 🔍 Troubleshooting
- Make sure USB access is enabled (disable Protection Mode in the add-on settings)
- Confirm your Webex token is valid
- Use `lsusb` or logs to confirm the Luxafor is detected (Vendor ID: `04d8`, Product ID: `f372`)


## 🌐 Links
- [Luxafor Python Library](https://github.com/vmitchell85/luxafor-python)
- [Home Assistant Add-on Docs](https://developers.home-assistant.io/docs/add-ons/overview/)

---
Made with ❤️ for focus and flow.

