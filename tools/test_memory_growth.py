def test_memory_growth(client):
    for i in range(20):
        client.post("/agent/query", json={"question": f"test {i}"})

    mem = client.get("/debug/memory").json()
    assert len(mem["short"]) > 0
    print("✅ test_memory_growth passed")