# Networking & 24/7 deployment

How to reach 空靈次元 from your phone and keep it running forever on the Mac Studio.

## 1. Local network (simplest, home only)

The server binds `0.0.0.0`, so on the same Wi-Fi the phone can open:

```
http://<mac-name>.local:4711      # e.g. http://mac-studio.local:4711
```

Enter your `AUTH_TOKEN` when prompted. Limitations: home Wi-Fi only, and iOS
will **not** install the full PWA over plain HTTP (no service worker on an
insecure origin). For the real installable app, use Tailscale below.

## 2. Tailscale — recommended (anywhere + HTTPS)

Gives the phone a private, encrypted route to the Mac from any network
(including cellular) with no router port-forwarding and no public exposure —
and a real `https://` hostname so the PWA installs properly on iOS.

```bash
# On the Mac Studio
brew install tailscale        # or the Tailscale.app
sudo tailscale up

# Expose the local server over HTTPS on your tailnet (MagicDNS + cert)
tailscale serve --bg 4711
tailscale serve status        # shows your https URL
```

Install Tailscale on the phone, sign into the same tailnet, then open the
`https://<mac-studio>.<tailnet>.ts.net` URL it printed. Enter your `AUTH_TOKEN`,
then **Add to Home Screen** (iOS Safari / Android Chrome) for a full-screen app.

> Keep `AUTH_TOKEN` set whenever the server is reachable beyond `localhost` —
> the backend rejects non-loopback requests without it.

## 3. Cloudflare Tunnel (optional, public sharing)

Only if you want people **outside** your tailnet to reach it (e.g. future
multiplayer). `cloudflared tunnel` gives a public `https://` endpoint with
automatic TLS and no open ports. Because it is public, the `AUTH_TOKEN` gate is
mandatory; consider Cloudflare Access in front as well.

## 4. Run 24/7 with launchd

`deploy/com.yao.pet.plist` starts the backend on login and restarts it on crash.

```bash
# Edit the plist: set the absolute repo path, your node path (`which node`),
# and run `npm -w @yao/server run start` (or `node` against a built server).
cp deploy/com.yao.pet.plist ~/Library/LaunchAgents/com.yao.pet.plist
launchctl load ~/Library/LaunchAgents/com.yao.pet.plist
launchctl start com.yao.pet

# logs
tail -f /tmp/yao.out.log /tmp/yao.err.log
```

Because the simulation derives state from elapsed time, restarts and reboots are
harmless — the pet catches up on the next tick.
