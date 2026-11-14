from fastapi import Request

from app.data_store import DataStore


def get_store(request: Request) -> DataStore:
    return request.app.state.store
