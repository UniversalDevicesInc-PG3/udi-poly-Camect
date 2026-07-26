
# Configure the Camect Node Server

If you don't have a Camect yet, or will be purchasing another one then please visit my link [Camect Affiliate link](https://camect.kckb.st/edc3936e) to purchase so I get credit for it.

You must set the following:

- user: The Camect local user.
- password: The Camect local user password

- Camect Host
    - Click 'Add Camect Host' for each of your Camect Hosts. Using camect.local may work if you only have one depending on your network. But probably best to use an IP address or hostname that is reserved in your router.

Until **user**, **password**, and at least one **Camect Host** are set, the controller **Errors** count stays non-zero and PG3 shows Notices such as “Please define user”. Those Notices and Errors clear once configuration is complete (and again if a hub later fails to connect, a connect Notice appears until it recovers).

Install pulls [jimboca/camect-py](https://github.com/jimboca/camect-py) into `camect-py/` and symlinks `camect` so the node server uses that client (needed for Host **Synced** status) until upstream releases the websocket connected-state APIs. The install host needs `git` available.

As noted in the [Camect Python client library](https://github.com/camect/camect-py/blob/master/README.md) Please open [Local Camect](https://local.home.camect.com/) in browser, sign in as admin and accept TOS before you proceed.  [Use a different user besides admin?](https://github.com/jimboca/udi-poly-Camect/issues/5)

## Camera Online vs Enabled

Each Camera node has:

- **Enabled** — camera is enabled in Camect (not the same as reachable)
- **Online** — camera is online per Camect `camera_online` / `camera_offline` events

ListCameras does not report online/offline, so after start Online is assumed True until an offline event arrives. Programs that care about reachability should use **Online**, not **Enabled**.

## Host connection status

Each Camect Host node shows **Camect Connected**:

| Value | Meaning |
|-------|---------|
| Disconnected | Cannot reach the hub (check host/IP, port, user, password, and that local access TOS was accepted) |
| Connected | Hub HTTP API answers; event websocket not open yet (or temporarily down) |
| Synced | Hub HTTP API and event websocket are both up — alerts and mode changes should flow |

If status stays on **Connected** and never reaches **Synced**, the hub is reachable over HTTPS but the event stream is failing (firewall, TLS/proxy, or hub restart). Once the hub is back online it should restore the connection, if not Restart the node server after fixing network access; it will reconnect and re-attach listeners.
