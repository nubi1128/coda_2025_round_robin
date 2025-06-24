# Round Robin Request Router

A lightweight Flask-based round-robin HTTP router  across multiple backend application instances.

## Features

- Round-Robin Load Balancing with strict sequential order check
- Dynamic Backend Discovery via DNS (Kubernetes `ClusterIP: None` headless service)
- Background Refresh Thread to detect scaling changes every 5 seconds
- Error Tolerance: gracefully retries if a target is unreachable
- Thread-safe Locking for consistent rotation
- Deployment to minikube and containerize

## Usage

This service exposes one POST endpoint:

```bash
POST /route
Content-Type: application/json
{
  "game": "pokemon",
  "gamerID": "Nova"
}
```

Your request will be forwarded to the next available `/payload` endpoint on a backend application server.

## stress-tested with `hey` with one single round robin server and three app server
```
bunnyli@MacBook-Air ~ % hey -n 100000 -c 200 \
    -m POST \
    -H "Content-Type: application/json" \
    -d '{"game":"pokemon","gamerID":"Nova"}' \
    http://127.0.0.1:50024/route


Summary:
  Total:	80.1517 secs
  Slowest:	1.1130 secs
  Fastest:	0.0013 secs
  Average:	0.1577 secs
  Requests/sec:	1247.6338
  
  Total data:	3500000 bytes
  Size/request:	35 bytes

Response time histogram:
  0.001 [1]	|
  0.112 [49827]	|■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
  0.224 [36945]	|■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
  0.335 [9771]	|■■■■■■■■
  0.446 [2427]	|■■
  0.557 [679]	|■
  0.668 [243]	|
  0.780 [51]	|
  0.891 [16]	|
  1.002 [32]	|
  1.113 [8]	|
```








eval $(minikube docker-env)
minikube service round-robin-api --url