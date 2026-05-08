FROM langchain/langgraph-api:3.12-wolfi

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY . /deps/
RUN cd /deps && uv pip install --system --no-cache .

COPY assistant/ /deps/assistant/
COPY langgraph.json /deps/

WORKDIR /deps

# LangGraph API automatically watches for file changes when LANGSERVE_GRAPHS is set
ENV LANGSERVE_GRAPHS='{"voice_agent": "/deps/assistant/graph.py:agent"}'

EXPOSE 8000
