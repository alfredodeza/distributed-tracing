import os
from flask import Flask, abort, request
import logging
import requests

# tracer stuff
from jaeger_client import Config

def init_tracer(service):
    logging.getLogger('').handlers = []
    logging.basicConfig(format='%(message)s', level=logging.DEBUG)

    config = Config(
        config={
            'sampler': {
                'type': 'const',
                'param': 1,
            },
            'local_agent': {
                'reporting_host': 'jaeger',
                'reporting_port': '6831',
            },
            'logging': True,
        },
        service_name=service,
    )

    return config.initialize_tracer()

app = Flask(__name__)
tracer = init_tracer("front-end")

backend = "http://back-end:5000"

@app.route("/")
def root():
    with tracer.start_span('root') as span:
        span.log_kv({'event': 'GET', 'route': '/'})
    return """
<h2>Distributed Sentiment Analysis</h2>
<p>Routes available for sentiment analysis:
  </br>
  <ul>
    <li><b>POST /sentiment</b>: Accepts JSON request, single object with "text" key. Value is analyzed and returned</li>
    <li><b>GET /health</b>: Distributed application health, returns JSON with backend microservice status</li>
  </ul>
  </br>
</p>
    """

@app.route("/sentiment", methods=["POST"])
def sentiment():
    with tracer.start_span('sentiment') as span:
        span.log_kv({'event': 'POST', 'route': '/sentiment'})
        span.set_tag("sentiment", "POST")
    endpoint = os.path.join(backend, "predict")
    response = requests.post(endpoint, json=request.json)
    try:
        response.raise_for_status()
        return response.json()
    except Exception as err:
        with tracer.start_span('sentiment') as span:
            span.log_kv({'event': 'POST', 'route': '/sentiment'})
            span.set_tag("error", str(err))



@app.route("/health")
def health():
    try:
        response = requests.get(backend)
        response.raise_for_status()
        return {"healthy": True, "error": None}
    except Exception as error:
        return {"healthy": False, "error": str(error)}

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
