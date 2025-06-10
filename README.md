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
bunnyli@Bunnys-MacBook-Pro coda_2025_round_robin % hey -n 50000 -c 100 \
    -m POST \
    -H "Content-Type: application/json" \
    -d '{"game":"pokemon","gamerID":"Nova"}' \
    http://127.0.0.1:61957/route


Summary:
  Total:	193.6459 secs
  Slowest:	0.8678 secs
  Fastest:	0.0403 secs
  Average:	0.3868 secs
  Requests/sec:	258.2032
  
  Total data:	1800000 bytes
  Size/request:	36 bytes

Response time histogram:
  0.040 [1]	|
  0.123 [36]	|
  0.206 [38]	|
  0.289 [60]	|
  0.371 [17488]	|■■■■■■■■■■■■■■■■■■■■■■■■■
  0.454 [27905]	|■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
  0.537 [3327]	|■■■■■
  0.620 [845]	|■
  0.702 [237]	|
  0.785 [24]	|
  0.868 [39]	|


Latency distribution:
  10% in 0.3245 secs
  25% in 0.3502 secs
  50% in 0.3861 secs
  75% in 0.4058 secs
  90% in 0.4471 secs
  95% in 0.4800 secs
  99% in 0.6002 secs
```


## Future Enhancements

- [ ] Replace in-memory state with Redis INCR for distributed routers
- [ ] Switch to `FastAPI + httpx` for async handling
- [ ] Add unit tests and performance benchmarks





eval $(minikube docker-env)