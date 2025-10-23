"""
Test GET RouteStatus command - CAREFULLY
"""
import asyncio
from das_trader import DASTraderClient


async def test_route_status():
    """Test if GET RouteStatus works without crashing DAS."""
    print("⚠️  TESTING GET RouteStatus COMMAND")
    print("=" * 70)
    print("This is a SAFE test - just checking if the command works")
    print()

    async with DASTraderClient(
        host='10.211.55.3',
        port=9910,
        log_level='INFO'  # Verbose to see everything
    ) as client:
        try:
            await client.connect(
                username='YOUR_USERNAME_HERE',
                password='YOUR_PASSWORD_HERE',
                account='YOUR_USERNAME_HERE'
            )
            print("✅ Connected to DAS")
            print()

            # Test the command
            print("📡 Sending: GET RouteStatus")
            print("Waiting for response...")
            print()

            response = await client.connection.send_command(
                "GET RouteStatus",
                wait_response=True,
                timeout=10.0
            )

            if response:
                print("✅ RESPONSE RECEIVED!")
                print("=" * 70)
                print(f"Response type: {type(response)}")
                print(f"Response length: {len(str(response))} chars")
                print()
                print("Raw response:")
                print("-" * 70)
                print(response)
                print("-" * 70)
                print()

                # Try to parse it
                if "$RouteStatus" in str(response):
                    print("✅ Contains $RouteStatus prefix - looks good!")

                    # Split into lines
                    lines = str(response).strip().split('\n')
                    print(f"\nFound {len(lines)} line(s)")

                    routes = []
                    for line in lines:
                        if "$RouteStatus" in line:
                            # Parse route info
                            # Format might be: $RouteStatus ROUTE_NAME STATUS ...
                            parts = line.split()
                            if len(parts) >= 2:
                                route_name = parts[1]
                                routes.append(route_name)
                                print(f"  - Route: {route_name}")

                    if routes:
                        print()
                        print(f"✅ Found {len(routes)} routes:")
                        for r in routes:
                            print(f"   • {r}")
                    else:
                        print("\n⚠️  Could not parse routes from response")
                else:
                    print("⚠️  Response doesn't contain $RouteStatus")
            else:
                print("❌ No response received (timeout or command not supported)")

            print()
            print("=" * 70)
            print("🎉 DAS IS STILL RUNNING - Command is SAFE!")
            print("=" * 70)

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_route_status())
