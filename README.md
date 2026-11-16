# Airbnb Holiday Traffic Spikes: Auto Scaling Proof of Concept

IT457 Cloud Computing Final Project, Group 14

A small AWS proof of concept inspired by Airbnb's move from a monolith to a service-oriented architecture (SOA). It shows how a stateless API behind a load balancer and an Auto Scaling Group behaves during a simulated holiday traffic spike.

**Team:** Suryadeepsinh Gohil (202301463), Prem Kukadiya (202301452), Prit Monpara (202611060)

## What it does

- A Flask API runs in Docker on EC2 (`t3.micro`) in AWS Mumbai (`ap-south-1`).
- An Application Load Balancer gives one public URL and sends traffic only to healthy instances.
- An Auto Scaling Group keeps 1 to 4 instances and targets 50% average CPU.
- k6 replays a holiday profile (2 to 25 requests per second) and CloudWatch records instance count and CPU.
- A single-page front-end at `/` shows listings, holiday pricing and a small "rush test".

## Experiments

| Run | Setup | Main finding |
|---|---|---|
| R1 | One fixed instance | Healthy up to about 10 req/s, fails above about 12 |
| R2 | Autoscaling, unhealthy threshold 5 | Instance was replaced before scale-out could happen |
| R2b | Autoscaling, unhealthy threshold 10 | Scaled out after about 5 minutes, scaled back in afterwards |
| R3 | Pre-scaled to 3 instances | Failures delayed by about 7 minutes |
| R4 | Autoscaling plus a manual instance failure | Group replaced the instance and reached 4, but too late for the peak |
| R5 | Path-based routing, two services | Catalog stayed at 2 to 3 ms while pricing was overloaded |

Full results, graphs and discussion are in the project report.

## API endpoints

| Endpoint | Purpose |
|---|---|
| `/health` | Load balancer health check |
| `/status` | Short JSON message with the instance id |
| `/work?n=...` | Bounded SHA-256 loop that creates CPU load |
| `/listings` | Static listings (light catalog service, R5) |
| `/search-pricing?n=...` | Holiday pricing with the same CPU loop (heavy pricing service, R5) |
| `/` | Front-end page |

## Repository layout

```
app/        Flask app, Dockerfile, static/index.html
infra/      EC2 start-up script (user_data.sh)
loadtest/   k6 script (loadtest.js)
analysis/   CloudWatch export and graph scripts (fetch_cloudwatch.py, analyze.py)
```

Live Load Balancer URL:** `http://abnb-poc-alb-2044815230.ap-south-1.elb.amazonaws.com`

Image tags: `v1` core endpoints, `v2` adds `/listings` and `/search-pricing`, `v3` adds the front-end. The image is built for `linux/amd64`.

## Tech stack

Python, Flask, Gunicorn, Docker, AWS (EC2, ALB, Auto Scaling, CloudWatch, S3, IAM), k6, pandas, Matplotlib, boto3.

## Notes

- The live AWS environment is shut down when not in use, so the load balancer URL may not respond.
- Results come from a small simulated test, with each run done once or twice, so they describe this proof of concept and not Airbnb.
- No keys or passwords are stored in this repository.
