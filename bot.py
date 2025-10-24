import discord
from discord.ext import commands
import os
import asyncio
import aiohttp
from dotenv import load_dotenv
import logging
import re
from flask import Flask         # <-- เพิ่มบรรทัดนี้
from threading import Thread    # <-- เพิ่มบรรทัดนี้

# ตั้งค่า Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('slip_bot')

# --- 1. โหลดค่า Config จาก .env ---
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
try:
    SLIP_CHANNEL_ID = int(os.getenv("SLIP_CHANNEL_ID"))
    STATUS_CHANNEL_ID = int(os.getenv("STATUS_CHANNEL_ID"))
except (ValueError, TypeError):
    logger.error("❌ ไม่พบ SLIP_CHANNEL_ID หรือ STATUS_CHANNEL_ID ในไฟล์ .env")
    exit()

if not TOKEN:
    logger.error("❌ ไม่พบ DISCORD_TOKEN ใน .env")
    exit()

# --- 2. ตั้งค่า SlipOK API ---
SLIP_API_KEY = os.getenv("SLIP_API_KEY") 
SLIP_API_ID = os.getenv("SLIP_API_ID", "55097")
SLIP_API_URL = f"https://api.slipok.com/api/line/apikey/{SLIP_API_ID}"

if not SLIP_API_KEY:
    logger.error("❌ ไม่พบ SLIP_API_KEY ใน .env")
    exit()

# --- ตั้งค่า Intents ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)


# --- ฟังก์ชันอัพเดท Status Channel ---
async def update_status_channel(member, months_to_add):
    """
    อัพเดท status channel โดยเพิ่ม ✅ ให้กับข้อความเดิมของ member
    ถ้าไม่มีข้อความเดิมจะสร้างใหม่
    """
    try:
        status_channel = bot.get_channel(STATUS_CHANNEL_ID)
        if not status_channel:
            logger.error(f"❌ ไม่พบ Status Channel ID: {STATUS_CHANNEL_ID}")
            return False
        
        # ค้นหาข้อความเดิมของ member นี้
        found_message = None
        async for msg in status_channel.history(limit=100):
            if msg.author == bot.user and member.mention in msg.content:
                # ตรวจสอบว่าข้อความนี้เป็นของ member ที่ต้องการ
                if msg.content.startswith(f"👤 ผู้ส่ง: {member.mention}"):
                    found_message = msg
                    break
        
        checkmarks_to_add = "✅ " * months_to_add
        
        if found_message:
            # แก้ไขข้อความเดิม - เพิ่ม ✅
            old_content = found_message.content
            
            # ดึงข้อมูลเดิมออกมา
            lines = old_content.split('\n')
            first_line = lines[0]
            
            # เพิ่ม checkmarks ใหม่
            new_content = first_line + checkmarks_to_add
            
            # ถ้ามีข้อมูลผู้ให้ เก็บไว้
            if len(lines) > 1:
                new_content += '\n' + '\n'.join(lines[1:])
            
            await found_message.edit(content=new_content)
            logger.info(f"✅ อัพเดทข้อความเดิมของ {member} สำเร็จ")
        else:
            # สร้างข้อความใหม่
            await status_channel.send(
                f"👤 ผู้ส่ง: {member.mention} : {checkmarks_to_add}"
            )
            logger.info(f"✅ สร้างข้อความใหม่สำหรับ {member} สำเร็จ")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ เกิดข้อผิดพลาดในการอัพเดท Status Channel: {e}")
        return False


# --- ตั้งค่า Intents ---
intents = discord.Intents.default()
# ... (โค้ดบอทของคุณ) ...
bot = commands.Bot(command_prefix="!", intents=intents)


# --- 🔽 เพิ่มส่วนนี้เข้าไปทั้งหมด 🔽 ---
app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run():
  app.run(host='0.0.0.0',port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
# --- 🔼 จบส่วนที่เพิ่ม 🔼 ---


# --- ฟังก์ชันอัพเดท Status Channel ---
async def update_status_channel(member, months_to_add):
# ... (โค้ดเดิมของคุณ) ...


@bot.event
async def on_ready():
    logger.info(f"✅ บอทล็อกอินเป็น {bot.user}")
    logger.info(f"👀 กำลังตรวจสอบห้อง ID: {SLIP_CHANNEL_ID}")
    logger.info(f"📊 Status Channel ID: {STATUS_CHANNEL_ID}")
    logger.info(f"🚀 ใช้ SlipOK API: {SLIP_API_URL}")
    logger.info(f"🔑 API Key: {SLIP_API_KEY}")


@bot.command()
@commands.has_permissions(administrator=True)
async def verify(ctx, member: discord.Member, months: int = 1):
    """
    (Admin) อัปเดตชื่อเล่นของสมาชิกเพื่อยืนยันการจ่ายเงิน
    """
    try:
        new_name = f"✅ {member.display_name} (จ่าย {months} เดือน)"
        if len(new_name) > 32:
            new_name = new_name[:29] + "..."
        await member.edit(nick=new_name)
        await ctx.send(f"อัปเดตชื่อ {member.mention} เป็น '{new_name}' แล้ว ✅")
    except discord.Forbidden:
        await ctx.send(f"❌ บอทไม่มีสิทธิ์ (Permission) พอที่จะเปลี่ยนชื่อ {member.mention}")
    except Exception as e:
        logger.error(f"Error in verify command: {e}")
        await ctx.send(f"❌ เกิดข้อผิดพลาดในการเปลี่ยนชื่อ: {e}")


# Error Handler สำหรับคำสั่ง verify
@verify.error
async def verify_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.send(
            "❌ **ไม่พบสมาชิกที่ระบุ**\n\n"
            "**วิธีใช้งาน:**\n"
            "`!verify @username [จำนวนเดือน]`\n\n"
            "**ตัวอย่าง:**\n"
            "• `!verify @Alice 1` - เติมให้ Alice 1 เดือน\n"
            "• `!verify @Bob 3` - เติมให้ Bob 3 เดือน\n\n"
            "**หมายเหตุ:** ต้อง @ (mention) ชื่อจริงๆ ไม่ใช่พิมพ์ @username"
        )
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            "❌ **ขาดข้อมูลที่จำเป็น**\n\n"
            "**วิธีใช้งาน:**\n"
            "`!verify @username [จำนวนเดือน]`\n\n"
            "**ตัวอย่าง:**\n"
            "`!verify @Alice 1`"
        )
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้ (ต้องเป็น Administrator)")
    else:
        logger.error(f"Unhandled error in verify command: {error}")
        await ctx.send(f"❌ เกิดข้อผิดพลาด: {error}")


# Error Handler สำหรับคำสั่ง verify
@verify.error
async def verify_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.send(
            "❌ **ไม่พบสมาชิกที่ระบุ**\n\n"
            "**วิธีใช้งาน:**\n"
            "`!verify @username [จำนวนเดือน]`\n\n"
            "**ตัวอย่าง:**\n"
            "• `!verify @Alice 1` - เติมให้ Alice 1 เดือน\n"
            "• `!verify @Bob 3` - เติมให้ Bob 3 เดือน\n\n"
            "**หมายเหตุ:** ต้อง @ (mention) ชื่อจริงๆ ไม่ใช่พิมพ์ @username"
        )
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            "❌ **ขาดข้อมูลที่จำเป็น**\n\n"
            "**วิธีใช้งาน:**\n"
            "`!verify @username [จำนวนเดือน]`\n\n"
            "**ตัวอย่าง:**\n"
            "`!verify @Alice 1`"
        )
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้ (ต้องเป็น Administrator)")
    else:
        logger.error(f"Unhandled error in verify command: {error}")
        await ctx.send(f"❌ เกิดข้อผิดพลาด: {error}")


@bot.command()
@commands.has_permissions(administrator=True)
async def monthly_reset(ctx):
    """
    (Admin) ลด ✅ ของทุกคนใน Status Channel ลง 1 เดือน
    ใช้คำสั่งนี้เมื่อผ่านไป 1 เดือนแล้ว
    """
    try:
        status_channel = bot.get_channel(STATUS_CHANNEL_ID)
        if not status_channel:
            await ctx.send(f"❌ ไม่พบ Status Channel ID: {STATUS_CHANNEL_ID}")
            return
        
        # เพิ่ม reaction เพื่อยืนยัน
        confirm_msg = await ctx.send(
            "⚠️ **คำเตือน: คุณกำลังจะลด ✅ ของทุกคนใน Status Channel ลง 1 เดือน**"
        )
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")
        
        def check(reaction, user):
            return (
                user == ctx.author and
                str(reaction.emoji) in ["✅", "❌"] and
                reaction.message.id == confirm_msg.id
            )
        
        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == "❌":
                await ctx.send("❌ ยกเลิกการรีเซ็ตแล้ว")
                return
            
            # เก็บข้อมูลสมาชิกทั้งหมด
            members_data = []
            
            # ดึงข้อความทั้งหมดจาก Status Channel
            async for message in status_channel.history(limit=200):
                if message.author == bot.user and message.content.startswith("👤 ผู้ส่ง:"):
                    try:
                        # ดึง mention ออกมา
                        lines = message.content.split('\n')
                        first_line = lines[0]
                        
                        # หา mention และนับ ✅
                        checkmark_count = message.content.count("✅")
                        
                        # ดึง member mention (รูปแบบ: 👤 ผู้ส่ง: @user : ✅ ✅)
                        if '<@' in first_line:
                            # ดึง member ID
                            member_id_match = re.search(r'<@!?(\d+)>', first_line)
                            if member_id_match:
                                member_id = int(member_id_match.group(1))
                                member = ctx.guild.get_member(member_id)
                                
                                if member and checkmark_count > 1:
                                    # เหลือมากกว่า 1 เดือน - ลดลง 1
                                    new_checkmarks = checkmark_count - 1
                                    members_data.append({
                                        'member': member,
                                        'checkmarks': new_checkmarks
                                    })
                        
                        # ลบข้อความเดิม
                        await message.delete()
                        await asyncio.sleep(0.3)
                        
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
            
            # สร้างข้อความใหม่ทั้งหมด
            if members_data:
                # เรียงตามจำนวน checkmarks จากมากไปน้อย
                members_data.sort(key=lambda x: x['checkmarks'], reverse=True)
                
                for data in members_data:
                    member = data['member']
                    checkmarks = "✅ " * data['checkmarks']
                    
                    await status_channel.send(
                        f"👤 ผู้ส่ง: {member.mention} : {checkmarks}"
                    )
                    await asyncio.sleep(0.3)  # หน่วงเวลาเพื่อไม่ให้ rate limit
            
            # แสดงผลลัพธ์
            total_members = len(members_data)
            logger.info(f"Monthly reset completed by {ctx.author}: {total_members} members remaining")
        
        except asyncio.TimeoutError:
            await ctx.send("⏰ หมดเวลา - ยกเลิกการรีเซ็ตแล้ว")
    
    except Exception as e:
        logger.error(f"Error in monthly_reset command: {e}")
        await ctx.send(f"❌ เกิดข้อผิดพลาด: {e}")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # ประมวลผลคำสั่ง !verify ก่อน
    await bot.process_commands(message)

    # ตรวจสอบว่าข้อความอยู่ในห้องที่กำหนด, มีไฟล์แนบ, และไม่ใช่บอท
    if message.channel.id == SLIP_CHANNEL_ID and message.attachments:
        
        for attachment in message.attachments:
            if attachment.content_type in ['image/png', 'image/jpeg', 'image/jpg']:
                
                logger.info(f"Processing slip from {message.author}: {attachment.filename}")
                
                try:
                    # --- ดาวน์โหลดรูปภาพจาก Discord ---
                    async with aiohttp.ClientSession() as session:
                        async with session.get(attachment.url) as img_response:
                            if img_response.status != 200:
                                await message.channel.send(f"❌ ไม่สามารถดาวน์โหลดรูปภาพได้")
                                continue
                            
                            image_data = await img_response.read()
                    
                    # เตรียม form data สำหรับ SlipOK API
                    form = aiohttp.FormData()
                    form.add_field('files', 
                                   image_data,
                                   filename=attachment.filename,
                                   content_type=attachment.content_type)
                    form.add_field('log', 'true')
                    
                    # ส่ง Request พร้อม API Key
                    headers = {
                        'x-authorization': SLIP_API_KEY
                    }
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            SLIP_API_URL,
                            data=form,
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=30)
                        ) as response:
                            
                            response_text = await response.text()
                            logger.info(f"SlipOK API Response Status: {response.status}")
                            logger.info(f"SlipOK API Response Body: {response_text}")
                            
                            try:
                                result = await response.json()
                            except Exception as json_error:
                                logger.error(f"JSON Parse Error: {json_error}")
                                await message.channel.send(
                                    f"❌ API ตอบกลับมาไม่ถูกต้อง (HTTP {response.status})\n"
                                    f"Response: {response_text[:200]}"
                                )
                                continue
                            
                            # --- ตรวจสอบผลลัพธ์ ---
                            if response.status == 200:
                                success = result.get('success', False)
                                
                                if success:
                                    # Slip ถูกต้อง
                                    data = result.get('data', {})
                                    
                                    receiver_name = data.get('receiver', {}).get('displayName', 'ไม่ทราบชื่อ')
                                    receiver_account = data.get('receiver', {}).get('account', {}).get('value', 'ไม่ทราบบัญชี')
                                    
                                    sender_name = data.get('sender', {}).get('displayName', 'ไม่ทราบชื่อ')
                                    sender_account = data.get('sender', {}).get('account', {}).get('value', 'ไม่ทราบบัญชี')
                                    
                                    amount = data.get('amount', 0)
                                    ref = data.get('transRef', 'ไม่มีเลข Ref')
                                    date_time = data.get('transDate', '') + ' ' + data.get('transTime', '')
                                    
                                    # คำนวณจำนวนเดือน (60 บาท = 1 เดือน)
                                    months = int(amount // 60)
                                    if months < 1:
                                        months = 1
                                    
                                    checkmarks = "✅ " * months
                                    
                                    # แสดงข้อมูลสลิป
                                    confirmation_msg = await message.channel.send(
                                        f"✅ **ตรวจพบสลิปถูกต้อง**\n"
                                        f"👤 ผู้ส่ง: {message.author.mention}\n"
                                        f"📄 ไฟล์: `{attachment.filename}`\n\n"
                                        f"**ข้อมูลการโอน:**\n"
                                        f"💰 จำนวนเงิน: **{amount:,.2f} บาท**\n"
                                        f"📤 ผู้โอน: {sender_name} ({sender_account})\n"
                                        f"📥 ผู้รับ: {receiver_name} ({receiver_account})\n"
                                        f"🔢 Ref: {ref}\n"
                                        f"📅 วันที่/เวลา: {date_time}\n"
                                        f"✓ ผ่านการตรวจสอบจาก SlipOK\n\n"
                                        f"📊 จำนวนเดือนที่ได้: **{months} เดือน** {checkmarks}\n\n"
                                        f"🎁 **ต้องการเติมให้ใครบางคน?**\n"
                                        f"กรุณา mention (@) คนที่ต้องการเติมให้ (สามารถเลือกได้ {months} คน)\n"
                                        f"ตัวอย่าง: @username หรือ @user1 @user2\n"
                                        f"หรือพิมพ์ `ตัวเอง` เพื่อเติมให้ตัวเอง\n"
                                        f"(มีเวลา 60 วินาที)"
                                    )
                                    
                                    def msg_check(m):
                                        return m.author == message.author and m.channel == message.channel
                                    
                                    try:
                                        user_msg = await bot.wait_for('message', timeout=60.0, check=msg_check)
                                        
                                        # ตรวจสอบว่าเลือก "ตัวเอง"
                                        if user_msg.content.strip().lower() in ['ตัวเอง', 'ตนเอง', 'me']:
                                            # เติมให้ตัวเอง
                                            success = await update_status_channel(message.author, months)
                                            if success:
                                                await message.channel.send(
                                                    f"✅ เติมให้ {message.author.mention} สำเร็จ! ({months} เดือน)"
                                                )
                                        
                                        elif len(user_msg.mentions) > 0:
                                            # มี mention คน
                                            selected_members = user_msg.mentions[:months]  # จำกัดตามจำนวนเดือน
                                            
                                            if months == 1:
                                                # 1 เดือน - เติมให้คนเดียว
                                                target = selected_members[0]
                                                success = await update_status_channel(target, 1)
                                                if success:
                                                    await message.channel.send(
                                                        f"✅ เติมให้ {target.mention} สำเร็จ! (1 เดือน)\n"
                                                        f"🎁 เติมให้โดย: {message.author.mention}"
                                                    )
                                            else:
                                                # หลายเดือน
                                                if len(selected_members) == 1:
                                                    # เลือกคนเดียว - เติมให้คนนั้นหมดเลย
                                                    target = selected_members[0]
                                                    success = await update_status_channel(target, months)
                                                    if success:
                                                        await message.channel.send(
                                                            f"✅ เติมให้ {target.mention} สำเร็จ! ({months} เดือน)\n"
                                                            f"🎁 เติมให้โดย: {message.author.mention}"
                                                        )
                                                else:
                                                    # เลือกหลายคน - แบ่งเท่าๆ กัน (1 เดือนต่อคน)
                                                    success_list = []
                                                    for target in selected_members:
                                                        success = await update_status_channel(target, 1)
                                                        if success:
                                                            success_list.append(target.mention)
                                                    
                                                    if success_list:
                                                        await message.channel.send(
                                                            f"✅ เติมให้ {', '.join(success_list)} สำเร็จ! (อย่างละ 1 เดือน)\n"
                                                            f"🎁 เติมให้โดย: {message.author.mention}\n"
                                                            f"📊 ใช้ไป {len(success_list)} เดือน จาก {months} เดือน"
                                                        )
                                        else:
                                            # ไม่มี mention - เติมให้ตัวเอง
                                            success = await update_status_channel(message.author, months)
                                            if success:
                                                await message.channel.send(
                                                    f"⚠️ ไม่พบการ mention ใคร - เติมให้ {message.author.mention} (ตัวเอง) แทน ({months} เดือน)"
                                                )
                                    
                                    except asyncio.TimeoutError:
                                        # หมดเวลา - เติมให้ตัวเอง
                                        success = await update_status_channel(message.author, months)
                                        if success:
                                            await message.channel.send(
                                                f"⏰ หมดเวลา! เติมให้ {message.author.mention} (ตัวเอง) แทน ({months} เดือน)"
                                            )
                                
                                else:
                                    # Slip ไม่ถูกต้อง
                                    error_message = result.get('message', 'ไม่สามารถตรวจสอบสลิปได้')
                                    await message.channel.send(
                                        f"⚠️ **สลิปไม่ผ่านการตรวจสอบ**\n"
                                        f"👤 ผู้ส่ง: {message.author.mention}\n"
                                        f"📄 ไฟล์: `{attachment.filename}`\n"
                                        f"❌ เหตุผล: {error_message}"
                                    )
                            
                            elif response.status == 401 or response.status == 403:
                                await message.channel.send(
                                    f"❌ **API Key ไม่ถูกต้อง** (HTTP {response.status})\n"
                                    f"กรุณาตรวจสอบ `SLIP_API_KEY` ในไฟล์ .env"
                                )
                                logger.error(f"Invalid API Key ({response.status})")
                            
                            else:
                                error_msg = result.get("message", "Unknown error")
                                await message.channel.send(
                                    f"❌ **เกิดข้อผิดพลาดในการตรวจสอบสลิป** (HTTP {response.status})\n"
                                    f"ข้อความ: {error_msg}"
                                )

                except asyncio.TimeoutError:
                    logger.error("API Timeout")
                    await message.channel.send(f"❌ API ตรวจสอบสลิปใช้เวลานานเกินไป (Timeout)")
                    
                except aiohttp.ClientError as e:
                    logger.error(f"HTTP Client Error: {e}")
                    await message.channel.send(f"❌ เกิดข้อผิดพลาดในการเชื่อมต่อ API: {e}")
                    
                except Exception as e:
                    logger.error(f"Unexpected error: {e}", exc_info=True)
                    await message.channel.send(f"❌ เกิดข้อผิดพลาดร้ายแรง: {e}")
                
            else:
                await message.channel.send(
                    f"⚠️ ไฟล์ `{attachment.filename}` ของ {message.author.mention} "
                    f"ไม่ใช่ไฟล์รูปภาพที่รองรับ (png, jpg, jpeg)"
                )


# Error Handler สำหรับคำสั่ง monthly_reset
@monthly_reset.error
async def monthly_reset_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้ (ต้องเป็น Administrator)")
    else:
        logger.error(f"Unhandled error in monthly_reset command: {error}")
        await ctx.send(f"❌ เกิดข้อผิดพลาด: {error}")
        

if __name__ == "__main__":
    logger.info("🚀 กำลังรันบอท...")
    keep_alive() # <-- เพิ่มบรรทัดนี้
    bot.run(TOKEN)