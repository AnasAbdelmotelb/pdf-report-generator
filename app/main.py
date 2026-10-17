from fastapi import FastAPI

app = FastAPI(title="PDF report generator")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
