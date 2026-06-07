
# Webhooks

Webhooks are a mechanism that allows your backend to receive notifications from Enode as they occur.

Integrate with webhooks so your application can receive updates about connected devices and accounts in near-real time, without having to constantly query our API.

To enable webhook events, you need to register webhook endpoints. After you register them, Enode can push near real-time notifications to your application’s webhook endpoint when events happen in your Enode account. Enode uses HTTPS to send webhook events to your endpoint as a JSON payload that includes up to 100 event objects.

Receiving webhook events is particularly useful for listening to asynchronous events such as when a vehicle has been plugged in, when a solar inverter has started producing, or when a thermostat temperature has changed. Webhooks are triggered whenever there is a change in the state of an asset, ensuring you receive timely updates. If there is no change in the asset's state, no webhook will be sent.

We will periodically send heartbeat events to your webhooks to ensure a continuous and reliable connection to Enode. These heartbeat events check the availability of your webhook and inform you how many events are queued for delivery. This helps you verify that your webhook integration is functioning correctly. Keep in mind that the number of queued events is an estimate and will typically be zero under normal operations.

## Get Started

To start receiving webhook events, create and register a webhook subscription using the [Create Webhook](https://developers.enode.com/api/reference#createWebhook) endpoint.

After registering a new webhook subscription, use the [Test Webhook](https://developers.enode.com/api/reference#testWebhook) endpoint to receive a test event. You can always use the [Update Webhook](https://developers.enode.com/api/reference#updateWebhook) endpoint to make any changes to your existing webhook subscriptions.

## Implementing your webhook endpoint

Your webhook endpoint should expect to receive `POST` requests bearing the following case insensitive headers:

| Header | Description |
| --- | --- |
| `x-enode-delivery` | Unique ID identifying the delivered payload |
| `x-enode-signature` | Signature authenticating that Enode is the author of the delivery |

And an `application/json` body containing an array of Events, with the following schema:

```json
[
  {
    "event": "user:vehicle:updated", // String - name of the event
    "createdAt": "2020-04-07T17:04:26Z", // UTC ISO 8601 - time at which the event was triggered
  },
  ...
]
```

Each event object may contain additional properties, depending on the event.

## Versioning

Webhook events are versioned. Every webhook event contains a `version` attribute that indicates the version used to generate the payload. If you don't specify an API version when creating the webhook, your client API version will be the one used for generating the payload. For information on how to change the client API version, see our [Versioning reference](https://developers.enode.com/api/reference#versioning). We recommend you use the `version` attribute in your webhook handler to future-proof your implementation, making it easier for you to handle future version changes.

## Security

There are several methods you can use to ensure the security of the communication between Enode and your servers.

### Payload integrity

A cryptographically secure secret should be generated and persisted on your server.

When you call [Create Webhook](https://developers.enode.com/api/reference#createWebhook), the secret must be provided. We use the secret to generate a signature on each webhook request. See [Verifying a payload signature](https://developers.enode.com/docs/webhooks#verifying-a-payload-signature) for instructions on using the secret to verify that the request originated from Enode.

It should be a pseudorandom value of at least 128 bits produced by a secure generator.

```javascript
// Node.js example - 256 bits
const crypto = require("crypto");
const secret = crypto.randomBytes(32).toString("hex");
```

### Verifying a payload signature

Requests to your endpoint will bear an `x-enode-signature` header verifying that the request has come from us.

The signature is the HMAC hex digest of the payload, where:

- algorithm = `sha1`
- key = your `secret` provided during webhook configuration
- payload = The request body (a UTF-8 encoded string containing JSON - be sure not to deserialize it before signature computation)

The signature is then prefixed with "sha1=". A delivery of `{"payload":"example"}` signed with `example-secret` would have an `x-enode-signature` of `sha1=e417e6fc2e7f8a78c93a35a7b344d36ce179fc8d`.

In Javascript, the signature may be verified as follows:

```javascript
// Node.js + Express example

// Read signature from request HTTP header
const enodeSignature = Buffer.from(req.get("x-enode-signature"), "utf8");

// Compute signature using your secret and the request payload
const payload = req.body;
const hmac = crypto.createHmac("sha1", <your secret>);
const digest = Buffer.from("sha1=" + hmac.update(payload).digest("hex"), "utf8");

// Check whether they match, using timing-safe equality (don't use ==)
if (!crypto.timingSafeEqual(digest, enodeSignature)) {
  throw new Error("Signature invalid");
}
```

### Authentication

Authentication is optional. If your endpoint requires authentication, you can configure an authentication header and value pair that will be sent on every request.

You can provide authentication configuration when using the [Create Webhook](https://developers.enode.com/api/reference#createWebhook) endpoint. For existing subscriptions you can enable, update or disable authentication using the [Update Webhook](https://developers.enode.com/api/reference#updateWebhook) endpoint. The header is case insensitive and will be transmitted lowercased.

Even if you have authentication configured, we strongly recommend you to verify the integrity of the request using the provided payload signature.

### IP addresses

As an additional security measure you can also verify that webhook events originate from an Enode IP address.

Webhook IP addresses are published for each environment subdomain as a `TXT` DNS record named `webhook-ips`. **These IPs can change. If you are going to use them, make sure you monitor the DNS record regularly.**

Run the following in your command-line to fetch the IPs:

- Production: `dig +short TXT webhook-ips.production.enode.com`
- Sandbox: `dig +short TXT webhook-ips.sandbox.enode.com`

## Timeouts, failures, and inactive webhooks

Webhook deliveries time out after 5 seconds. After a failed delivery, we will attempt to redeliver your events over **24 hours** in increasing intervals. If any of the retry attempts succeeds, the webhook will be considered healthy again. But if all retry attempts fail, all pending events will be deleted and your webhook marked as inactive.

Sandbox thresholds: Because of how sandbox is used for testing, we'll make fewer delivery retries. If you endpoint fails to process notifications for 5 minutes it'll be marked as inactive.

If a webhook becomes inactive, it can be reactivated in one of 2 ways:

- Use the [Test Webhook](https://developers.enode.com/api/reference#testWebhook) endpoint
- You can update the webhook using the [Update Webhook](https://developers.enode.com/api/reference#updateWebhook) endpoint

## Best Practices

### Handle versioned payloads

To future-proof your implementation, we recommend that you either pin your subscription version using the [Create Webhook](https://developers.enode.com/api/reference#createWebhook) or [Update Webhook](https://developers.enode.com/api/reference#updateWebhook) endpoints; or you use the `version` attribute in each webhook event to inform your implementation. This will ensure a graceful transition between versions.

### Respond within 5 seconds

Your server should respond with a 2XX response within 5 seconds of receiving a webhook delivery. If your server takes longer than that to respond, then Enode terminates the connection and considers the delivery a failure.

In order to respond in a timely manner, you may want to set up a queue to process webhook payloads asynchronously. Your server can respond when it receives the webhook, and then process the payload in the background without blocking future webhook deliveries.

### Only listen to event types your integration requires

Configure your webhook endpoints to receive only the types of events required by your integration. Listening for extra events (or all events) puts undue strain on your server and we don’t recommend it.

You can change the events that a webhook endpoint receives when you [create](https://developers.enode.com/api/reference#createWebhook) or [update](https://developers.enode.com/api/reference#updateWebhook) a webhook.

## Supported events

You can find the list of supported events in the [Webhook events section](https://developers.enode.com/api/reference/#webhook-events) of the API reference.
