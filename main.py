
import os
import nextcord
import threading
from datetime import datetime
from dotenv import load_dotenv
from compositeai.drivers import OpenAIDriver
from compositeai.agents import AgentResult
from compositeai.tools import GoogleSerperApiTool, WebScrapeTool
from agent import Agent

# Bot constants
TRIGGER_PHRASE = "hey susbot"

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Discord client init
intents = nextcord.Intents.all()
client = nextcord.Client(intents=intents)

# Inititialize Composite.ai agent
agent = Agent(
    driver=OpenAIDriver(model="gpt-4o-mini"),
    description="""
    You are a helpful Discord chat bot named Susbot.
    You can use Google and scrape websites to help answer questions.
    """,
    tools=[GoogleSerperApiTool(), WebScrapeTool()],
    max_iterations=10,
)

# Per-user rate limit parameters
rate_limit_period = 5  # Seconds between allowed command executions for each user
user_last_command_time = {}  # Dictionary to track the last command time for each user

async def rate_limiter(message):
    user_id = message.author.id
    current_time = datetime.now()

    # Check if the user has executed a command before
    if user_id in user_last_command_time:
        time_since_last_command = (current_time - user_last_command_time[user_id]).total_seconds()

        if time_since_last_command < rate_limit_period:
            remaining_time = rate_limit_period - time_since_last_command
            await message.channel.send(f"<@{user_id}>, please wait {remaining_time:.1f} seconds before using another command.")
            return False

    # Update the last command time for this user
    user_last_command_time[user_id] = current_time
    return True

# Background task to reset the rate limit dictionary every hour
def reset_rate_limit():
    global user_last_command_time
    user_last_command_time = {}
    threading.Timer(3600, reset_rate_limit).start()

threading.Timer(3600, reset_rate_limit).start()

# Discord on message event    
@client.event
async def on_message(message):
    if message.content.lower().startswith(TRIGGER_PHRASE) and not message.author.bot:
        if await rate_limiter(message):
            await chat(message)

# Function for chat completion
async def chat(message):
    async with message.channel.typing():
        try:
            for chunk in agent.execute(message.content, stream=True):
                if isinstance(chunk, AgentResult):
                    agent_result = chunk.content
                    await message.channel.send(agent_result)
        except Exception as e:
            await message.channel.send(f"Sorry, I ran into the following error: {e}")

client.run(TOKEN)