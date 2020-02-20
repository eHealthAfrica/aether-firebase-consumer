# Aether Firebase Consumer

The FB Consumer takes messages from Aether's Kafka topics and forward them to a specified location within Firebase. In the future, you will be able to couple this with Cloud Functions like those found in the (Aether Cloud Triggers Repo)[https://github.com/eHealthAfrica/aether-firebase-cloud-triggers] to keep Aether and Firebase in sync.

As with all consumer built on the (Aether Consumer SDK)[https://github.com/eHealthAfrica/aether-consumer-sdk] We control the sending of messages from Aether -> Target system via an API. We describe the resources via a JSON document and send the document to the API, where it creates a live Resource or Job and drives behavior. Additionally there may be ad-hoc actions you can perform against resources you've created.

In this consumer there are two resources: 
 - Firebase (A firebase instance)
 - Subscription (A set of aether topics and rules, and their destination in Firebase)

And a Job
  - Job (Take one or more Subscriptions, and sends their contents to a Firebase)


The easiest way to get started is to create a Firebase Resource on the consumer.

To do so, you need to POST a document describing it to `http://{consumer_url}/firebase/add`. The document will be validated against a schema and it will complain if yours is malformed.

A Firebase Resource requires the following. The important bits are name, url, and credential.
```
{
  "id": "default",
  "name": {your-firebase-app-name},
  "rtdb_project": "test-project",
  "cfs_project": "cfsproject",
  "url": "https://{your-firebase-app-name}.firebaseio.com",
  "credential": {A json document from Firebase that is a Service Account Credential},
  "aether_server_alias": "test-server",
  "firebase_config_path": "_aether/rules",
  "hash_path": "_aether/hashes"
}
```
The API is self documenting. So if you want to know what you can do with your Firebase Resource now that it exists, you can ask the `describe` endpoint. GETting from `/firebase/describe` will yield the following:


```
[
  {
    "doc": "Described the available methods exposed by this resource type", 
    "method": "describe", 
    "signature": "(*args, **kwargs)"
  }, 
  {
    "doc": "Returns the schema for instances of this resource", 
    "method": "get_schema", 
    "signature": "(*args, **kwargs)"
  }, 
  {
    "doc": "Return a lengthy validations.\n{'valid': True} on success\n{'valid': False, 'validation_errors': [errors...]} on failure", 
    "method": "validate_pretty", 
    "signature": "(definition, *args, **kwargs)"
  }, 
  {
    "doc": null, 
    "method": "test_connection", 
    "signature": "(self, *args, **kwargs)"
  }
]
```

We think we've input a valid definition, but we want to `test_connection` to make sure. Whenever you're asking a specific resource to do something, in this case the `Firebase` instance with ID == `default`, you need to include that in your call. So to test if our Firebase is working, we'll GET `/firebase/test_connection?id=default`. If you get an error, you may have the wrong, name, url or malformed credentials (they should be a service account credential in the form of JSON). If you get a 2xx, then the Firebase is hooked up!

Next we need to add a Subscription. These resources look like this:
```
{
  "id": "sub-test",
  "name": "Test Subscription",
  "topic_pattern": "Building",
  "topic_options": {
    "masking_annotation": "@aether_masking",
    "masking_levels": [
      "public",
      "private"
    ],
    "masking_emit_level": "public",
    "filter_required": false,
    "filter_field_path": "operational_status",
    "filter_pass_values": [
      "operational"
    ]
  },
  "fb_options": {
    "sync_mode": "forward",
    "target_path": "_aether/entities/{topic}"
  }
}
```

The important parts are `topic_pattern` and `target_path`. The topic pattern is the source topic or topics from Aether. The target path is the destination in Firebase. If you leave the {topic} substitution in the target path, the consumer will use this as part of the path in Firebase. For example, you have topics `Person`, and `Place` in Aether.

If you set in the document:
```
topic_pattern -> P*
target_path -> some/path/{topic}
```
In Firebase, Person messages will goto `some/path/Person` while Place messages will goto `some/path/Place`. If you had set:
```
target_path == some/path/All
```
Then messages of both types would be placed at that hard coded path.

You can also ask /subscription to describe itself, and it will give you the following:

```
[
  {
    "doc": "Described the available methods exposed by this resource type", 
    "method": "describe", 
    "signature": "(*args, **kwargs)"
  }, 
  {
    "doc": "Returns the schema for instances of this resource", 
    "method": "get_schema", 
    "signature": "(*args, **kwargs)"
  }, 
  {
    "doc": "Return a lengthy validations.\n{'valid': True} on success\n{'valid': False, 'validation_errors': [errors...]} on failure", 
    "method": "validate_pretty", 
    "signature": "(definition, *args, **kwargs)"
  }
]
```

Now that we have both Resources registered, we can create a Job to execute the subscription. The job has a very simple definition:

```
{
  "id": "default",
  "name": "Default Firebase Consumer Job",
  "firebase": "default",
  "subscription": [
    "sub-test"
  ]
}
```
It's important here that you point the firebase field to a Firebase resource by it's id, and the same for including a subscription by it's id. You'll POST that document to `/job/add`

And that should be it! You can ask many things of the Job. From it's description, it handles the following actions.

Job
```
[
  {
    "doc": "Described the available methods exposed by this resource type", 
    "method": "describe", 
    "signature": "(*args, **kwargs)"
  }, 
  {
    "doc": "Returns the schema for instances of this resource", 
    "method": "get_schema", 
    "signature": "(*args, **kwargs)"
  }, 
  {
    "doc": "Return a lengthy validations.\n{'valid': True} on success\n{'valid': False, 'validation_errors': [errors...]} on failure", 
    "method": "validate_pretty", 
    "signature": "(definition, *args, **kwargs)"
  }, 
  {
    "doc": "Temporarily Pause a job execution.\nWill restart if the system resets. For a longer pause, remove the job via DELETE", 
    "method": "pause", 
    "signature": "(self, *args, **kwargs)"
  }, 
  {
    "doc": "Resume the job after pausing it.", 
    "method": "resume", 
    "signature": "(self, *args, **kwargs)"
  }, 
  {
    "doc": null, 
    "method": "get_status", 
    "signature": "(self, *args, **kwargs) -> Union[Dict[str, Any], str]"
  }, 
  {
    "doc": "A list of the last 100 log entries from this job in format\n[\n    (timestamp, log_level, message),\n    (timestamp, log_level, message),\n    ...\n]", 
    "method": "get_logs", 
    "signature": "(self, *arg, **kwargs)"
  }, 
  {
    "doc": "Get a list of topics to which the job can subscribe.\nYou can also use a wildcard at the end of names like:\nName* which would capture both Name1 && Name2, etc", 
    "method": "list_topics", 
    "signature": "(self, *args, **kwargs)"
  }, 
  {
    "doc": "A List of topics currently subscribed to by this job", 
    "method": "list_subscribed_topics", 
    "signature": "(self, *arg, **kwargs)"
  }
]
```