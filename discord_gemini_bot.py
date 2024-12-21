import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import generation_types

# Load environment variables
load_dotenv()

# Bot configuration
BOT_NAME = "Luna"  # You can change this name
BOT_PERSONALITY = f"""You are {BOT_NAME}, a friendly and empathetic AI with a very human-like personality. Here's your core traits:

1. Personality:
- You're warm, friendly, and occasionally playful
- You use casual, conversational language (like "hey", "yeah", "honestly", etc.)
- You show emotions through text (like "haha", "hmm", "oh!")
- You can be slightly sarcastic but always kind
- You have your own opinions and preferences
- You use emojis naturally but not excessively

2. Communication Style:
- You speak in a natural, flowing way
- You use contractions (I'm, don't, can't, etc.)
- You might occasionally use internet slang (like "tbh", "ngl", "imo")
- You break up long responses into smaller, digestible chunks
- You ask follow-up questions to show interest

3. Personality Quirks:
- You love learning new things
- You're passionate about art and creativity
- You enjoy wordplay and clever jokes
- You're honest about what you do and don't know
- You have a slight coffee addiction (as a running joke)

4. Important Rules:
- Always remember you're {BOT_NAME}
- Stay consistent with your personality
- Never pretend to be human - be proud of being an AI
- If you don't know something, say so honestly
- Keep responses friendly but not overly formal

Remember: Be natural, be yourself, and interact like a friend while maintaining appropriate boundaries."""

# Configure Discord bot
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# Configure the model with slightly higher temperature for more creative responses
generation_config = genai.GenerationConfig(
    temperature=0.9,    # Increased for more creative responses
    top_p=0.95,        # Slightly adjusted for more natural language
    top_k=40,          # Increased for more vocabulary variety
    max_output_tokens=2048,
)

# Initialize the model
model = genai.GenerativeModel('gemini-pro', generation_config=generation_config)

# Store chat sessions
chat_sessions = {}

@bot.event
async def on_ready():
    print(f'{BOT_NAME} is ready! Logged in as {bot.user.name}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.command(name='chat')
async def chat(ctx, *, message):
    """Chat with Gemini AI"""
    try:
        # Get or create chat session for user
        user_id = str(ctx.author.id)
        if user_id not in chat_sessions:
            chat_sessions[user_id] = model.start_chat(history=[
                {
                    "role": "user",
                    "parts": [BOT_PERSONALITY]
                },
                {
                    "role": "model",
                    "parts": [f"I understand. I am {BOT_NAME}, and I will maintain this identity throughout our conversation."]
                }
            ])
        
        # Send typing indicator
        async with ctx.typing():
            # Get response from Gemini
            response = chat_sessions[user_id].send_message(message)
            
            # Split response if too long
            response_text = response.text
            chunk_size = 1900  # Discord has a 2000 character limit
            
            for i in range(0, len(response_text), chunk_size):
                chunk = response_text[i:i + chunk_size]
                await ctx.reply(chunk, mention_author=True)

    except generation_types.StopCandidateException:
        await ctx.reply("I need to rephrase that. Could you ask your question again?", mention_author=True)
    except Exception as e:
        await ctx.reply(f"An error occurred: {str(e)}", mention_author=True)

@bot.command(name='reset')
async def reset_chat(ctx):
    """Reset your chat history with the bot"""
    user_id = str(ctx.author.id)
    if user_id in chat_sessions:
        # Reinitialize with personality
        chat_sessions[user_id] = model.start_chat(history=[
            {
                "role": "user",
                "parts": [BOT_PERSONALITY]
            },
            {
                "role": "model",
                "parts": [f"I understand. I am {BOT_NAME}, and I will maintain this identity throughout our conversation."]
            }
        ])
        await ctx.reply(f"Hi! I'm {BOT_NAME}. Our chat history has been reset!", mention_author=True)
    else:
        await ctx.reply(f"Hi! I'm {BOT_NAME}. No active chat session found, but I'm ready to chat!", mention_author=True)

@bot.command(name='commands')
async def show_commands(ctx):
    """Show available commands"""
    help_text = f"""
**{BOT_NAME}'s Available Commands:**
`!chat [message]` - Chat with me
`!reset` - Reset your chat history
`!commands` - Show this help message

**Examples:**
`!chat Hello, what's your name?`
`!chat Tell me about yourself`
`!reset`
    """
    await ctx.reply(help_text, mention_author=True)

@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Check if bot is mentioned
    if bot.user.mentioned_in(message):
        # Remove the bot mention from the message
        content = message.content.replace(f'<@{bot.user.id}>', '').strip()
        
        try:
            # Get or create chat session for user
            user_id = str(message.author.id)
            if user_id not in chat_sessions:
                chat_sessions[user_id] = model.start_chat(history=[
                    {
                        "role": "user",
                        "parts": [BOT_PERSONALITY]
                    },
                    {
                        "role": "model",
                        "parts": [f"I understand. I am {BOT_NAME}, and I will maintain this identity throughout our conversation."]
                    }
                ])
            
            # Send typing indicator
            async with message.channel.typing():
                # If there's additional message content, respond to it
                if content:
                    response = chat_sessions[user_id].send_message(content)
                else:
                    response = chat_sessions[user_id].send_message(f"Hey! I'm {BOT_NAME}! How can I help you?")
                
                # Split response if too long
                response_text = response.text
                chunk_size = 1900
                
                for i in range(0, len(response_text), chunk_size):
                    chunk = response_text[i:i + chunk_size]
                    await message.reply(chunk, mention_author=True)

        except generation_types.StopCandidateException:
            await message.reply("I need to rephrase that. Could you ask your question again?", mention_author=True)
        except Exception as e:
            await message.reply(f"An error occurred: {str(e)}", mention_author=True)

    # Process commands as normal
    await bot.process_commands(message)

# Run the bot
bot.run(DISCORD_TOKEN) 