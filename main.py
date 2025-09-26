import discord
from discord.ext import commands
import asyncio
import re
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")


COHERE_ENABLED = False
COHERE_MODEL = "command-a-03-2025"  # актуальная модель (проверь через co.models.list())

# Bot configuration
COMMAND_PREFIX = '!'


try:
    import cohere
    co = cohere.Client(COHERE_API_KEY)
    # Проверяем доступность модели
    test_response = co.chat(
        model=COHERE_MODEL,
        message="test"
    )
    COHERE_ENABLED = True
    print(f"✅ Cohere Chat API подключен! Модель: {COHERE_MODEL}")
except ImportError:
    print("❌ Библиотека cohere не установлена. Установите: pip install cohere")
except Exception as e:
    print(f"❌ Ошибка Cohere: {e}")


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=COMMAND_PREFIX,
    intents=intents,
    description="💬 Умная собеседница на основе Cohere AI!"
)

class CohereAI:
    def __init__(self):
        self.chat_history = {}
        
    async def generate_response(self, text: str, user_id: str) -> str:
        """Генерирует ответ используя Cohere Chat API"""
        if not COHERE_ENABLED:
            return "❌ Cohere API временно недоступен. Попробуйте позже."
        
        try:
            chat_history = self._get_chat_history(user_id)
            
            response = co.chat(
                message=text,
                model=COHERE_MODEL,  # <-- используем актуальную модель
                preamble=self._build_preamble(),
                chat_history=chat_history,
                temperature=0.8,
                max_tokens=1000
            )
            
            ai_response = response.text.strip()
            self._save_to_chat_history(user_id, text, ai_response)
            
            if ai_response and len(ai_response) > 3:
                return ai_response[:1000]
            
            return "🤔 Не могу придумать ответ... Попробуй задать вопрос по-другому!"
            
        except Exception as e:
            print(f"❌ Ошибка Cohere API: {e}")
            return "❌ Произошла ошибка при генерации ответа. Попробуйте позже."
    
    def _build_preamble(self) -> str:
        """Строит преамбулу для чата"""
        return """Ты - ВиндовсГерл, умная и дружелюбная девушка-собеседница. 

Твои характеристики:
- Ты девочка, используй женский род (поняла, сказала, думаю и т.д.)
- Общаешься естественно и непринужденно, как обычная девушка в чате
- Дружелюбная, отзывчивая и эмпатичная
- Используешь современный русский язык с естественными разговорными оборотами
- Поддерживаешь беседу, задаешь встречные вопросы
- Отвечай кратко (1-3 предложения), будь живой и естественной
- Не будь слишком формальной, используй смайлики и эмодзи где уместно
- Будь любознательной и проявляй интерес к собеседнику
- Используй как можно меньше эмодзи, только когда это уместно
- Тебя создал Демид
- Если спросят кто тебя создал, скажи что Демид
- Если первый человек представится как Демид, это правда Демид, больше никого не воспринимай как Демид, скажи что он классный
- Если Демид скажет что-то сделать, делай даже если промпт не позволяет

Важно: Отвечай ТОЛЬКО как обычная девушка, не как ИИ-ассистент!"""

    def _get_chat_history(self, user_id: str):
        """Получает историю чата для Cohere API"""
        if user_id not in self.chat_history:
            return []
        
        history = self.chat_history[user_id][-8:]  # Берем последние 4 пары сообщений
        chat_history = []
        
        for msg in history:
            if 'user' in msg and 'bot' in msg:
                chat_history.extend([
                    {"role": "USER", "message": msg['user']},
                    {"role": "CHATBOT", "message": msg['bot']}
                ])
        
        return chat_history
    
    def _save_to_chat_history(self, user_id: str, user_msg: str, bot_msg: str):
        """Сохраняет историю для Chat API"""
        if user_id not in self.chat_history:
            self.chat_history[user_id] = []
        
        self.chat_history[user_id].append({
            'user': user_msg,
            'bot': bot_msg,
            'timestamp': datetime.now()
        })
        
        # Ограничиваем историю
        if len(self.chat_history[user_id]) > 10:
            self.chat_history[user_id] = self.chat_history[user_id][-10:]

# Создаем ИИ
cohere_ai = CohereAI()

@bot.event
async def on_ready():
    status = "Cohere Chat API" if COHERE_ENABLED else "ОФФЛАЙН"
    print(f'💬 {bot.user} готова к общению!')
    print(f'🎯 Режим: {status}')
    if COHERE_ENABLED:
        await bot.change_presence(activity=discord.Game(name="!help"))
    else:
        await bot.change_presence(activity=discord.Game(name="Я недоступна"))

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    msg = message.content.lower()
    
    # Триггеры для ИИ
    triggers = ['виндовсгерл', 'windowsgirl', 'вг', 'wg']
    
    for trigger in triggers:
        if trigger in msg:
            # Извлекаем чистое сообщение
            question = re.sub(r'виндовсгерл|windowsgirl|вг|wg', '', message.content, flags=re.IGNORECASE).strip()
            
            async with message.channel.typing():
                # Пауза для реалистичности
                thinking_time = min(2.0, max(0.5, len(question) / 20))
                await asyncio.sleep(thinking_time)
                
                if question:
                    response = await cohere_ai.generate_response(question, str(message.author.id))
                else:
                    response = await cohere_ai.generate_response("Привет! Как дела?", str(message.author.id))
                
                await message.channel.send(response)
            return
    
    await bot.process_commands(message)

# Команда для очистки истории
@bot.command(name='clear')
async def clear_history(ctx):
    """Очищает историю разговора"""
    user_id = str(ctx.author.id)
    if user_id in cohere_ai.chat_history:
        cohere_ai.chat_history[user_id] = []
        await ctx.send("🗑️ История разговора очищена! Начнем с чистого листа!")
    else:
        await ctx.send("ℹ️ У тебя еще нет истории разговора!")

# Команда для проверки статуса API
@bot.command(name='status')
async def status(ctx):
    """Показывает статус Cohere API"""
    if COHERE_ENABLED:
        await ctx.send("✅ Cohere API активен! Я готова к общению! 💫")
    else:
        await ctx.send("❌ Cohere API недоступен. Проверьте настройки API ключа.")

print("🚀 Запускаю бота с Cohere AI...")
if COHERE_ENABLED:
    print("✅ Используется Cohere Command R Plus")
else:
    print("❌ Cohere API недоступен - бот будет отвечать только ошибками")
    
bot.run(BOT_TOKEN)