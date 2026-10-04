import asyncio
import httpx
from app.main import app
from app.services.outbox_dispatcher import outbox_dispatcher_service

async def run_outbox_tests():
    """
    Test suite for Module 5: Outbox Dispatcher & Safeguards.
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Check initial stats
        res_stats = await client.get("/api/v1/outbox/stats")
        stats = res_stats.json()
        print(f"\n--- Initial Pipeline Stats ---")
        print(f"Daily Limit: {stats['daily_limit']} | Sent Today: {stats['sent_today']} | Remaining: {stats['remaining_today']}")
        assert res_stats.status_code == 200

        # Test 1: Queue a Draft
        print("\n--- Test 1: Save Email as Draft ---")
        payload_draft = {
            "recipient_email": "sarah.jenkins@stripe.com",
            "recipient_name": "Sarah Jenkins",
            "company_name": "Stripe",
            "subject_line": "Quick note regarding Full-Stack Engineer @ Stripe",
            "body": "Hi Sarah, I'm reaching out...",
            "mode": "draft"
        }
        res_draft = await client.post("/api/v1/outbox/queue", json=payload_draft)
        item_draft = res_draft.json()
        print(f"Draft Created: ID={item_draft['id']} | Status={item_draft['status']} | Note={item_draft['note']}")
        assert res_draft.status_code == 200
        assert item_draft["status"] == "draft"

        # Test 2: Live Send within Limit
        print("\n--- Test 2: Live Send (Within Rate Limits) ---")
        payload_send = {
            "recipient_email": "elena.rostova@datadoghq.com",
            "recipient_name": "Elena Rostova",
            "company_name": "Datadog",
            "subject_line": "Quick note regarding Backend Engineer @ Datadog",
            "body": "Hi Elena, I've been following Datadog's architecture...",
            "mode": "live_send"
        }
        res_send = await client.post("/api/v1/outbox/queue", json=payload_send)
        item_send = res_send.json()
        print(f"Item Dispatched: ID={item_send['id']} | Status={item_send['status']} | SentAt={item_send['sent_at']}")
        assert res_send.status_code == 200
        assert item_send["status"] == "sent"

        # Test 3: Trigger Daily Limit Safeguard
        print("\n--- Test 3: Velocity Safeguard Protection ---")
        # Temporarily set daily limit low to test safeguard behavior
        original_limit = outbox_dispatcher_service.daily_limit
        outbox_dispatcher_service.daily_limit = 1 # We already sent 1!

        payload_exceeded = {
            "recipient_email": "alex.morgan@vercel.com",
            "recipient_name": "Alex Morgan",
            "company_name": "Vercel",
            "subject_line": "Frontend / Next.js inquiry",
            "body": "Hi Alex...",
            "mode": "live_send"
        }
        res_safeguard = await client.post("/api/v1/outbox/queue", json=payload_exceeded)
        item_safeguard = res_safeguard.json()
        print(f"Safeguard Result: Status={item_safeguard['status']} | Note={item_safeguard['note']}")
        assert item_safeguard["status"] == "queued_for_tomorrow"

        # Reset limit
        outbox_dispatcher_service.daily_limit = original_limit

        # Test 4: List all items
        print("\n--- Test 4: Query Outbox Pipeline ---")
        res_list = await client.get("/api/v1/outbox/items")
        all_items = res_list.json()
        print(f"Total Tracked Items in Pipeline: {len(all_items)}")
        assert len(all_items) >= 3

    print("\n==========================================")
    print(">>> MODULE 5 OUTBOX TESTS PASSED! <<<")
    print("==========================================\n")

if __name__ == "__main__":
    asyncio.run(run_outbox_tests())
