#!/usr/bin/env python3
"""Quick API test script."""
import asyncio
import httpx

BASE_URL = "http://localhost:8000"


async def test_health():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/health")
        print("✓ Health check:", response.json())


async def test_create_validation():
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            f"{BASE_URL}/api/validations",
            json={"idea": "AI-powered pitch deck generator"},
        )
        data = response.json()
        print("✓ Created validation:", data["id"])
        return data["id"]


async def test_get_validation(run_id: str):
    async with httpx.AsyncClient() as client:
        # Wait a bit for processing
        await asyncio.sleep(5)
        response = await client.get(f"{BASE_URL}/api/validations/{run_id}")
        data = response.json()
        print(f"✓ Validation status: {data['status']}")
        if data.get("synthesis"):
            print(f"  Verdict: {data['synthesis']['verdict']}")
            print(f"  Confidence: {data['synthesis']['confidence']:.0%}")


async def main():
    print("Testing Maverick API...\n")
    await test_health()
    run_id = await test_create_validation()
    await test_get_validation(run_id)
    print("\n✓ All tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
