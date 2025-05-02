from telegram_listener import start_listener
from telegram_callback_handler import client as callback_client
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def main():
    # Start the callback handler
    await callback_client.start()
    
    # Run the signal listener in a separate thread
    with ThreadPoolExecutor() as executor:
        # Run the signal listener in a thread
        executor.submit(start_listener)
        
        # Keep the callback handler running
        await callback_client.run_until_disconnected()

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
