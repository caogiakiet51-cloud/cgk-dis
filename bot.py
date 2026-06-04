import discord
from discord.ext import commands
from discord import ui, ButtonStyle
from discord import ui, SelectOption
import random
import asyncio
import json
import os
import time
from flask import Flask
from threading import Thread

# --- CẤU HÌNH HỆ THỐNG TỐI CAO ---
OWNER_ID = 851328559301656606  # ID Chủ sòng của bạn
token = os.environ.get('TOKEN')
DB_FILE = "database.json"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="cgk ", intents=intents, help_command=None)

# --- KHỞI TẠO VÀ QUẢN LÝ DATABASE TOÀN DIỆN ---
def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_user(user_id):
    db = load_db()
    uid = str(user_id)
    
    if uid not in db or not isinstance(db[uid], dict):
        old_balance = db[uid] if (uid in db and isinstance(db[uid], (int, float))) else 50000
        db[uid] = {
            "balance": old_balance,
            "xp": 0,
            "level": 1,
            "last_daily": 0,
            "inventory": {
                "weapons": [],
                "animals": []
            }
        }
        save_db(db)
    else:
        default_keys = {
            "balance": 50000,
            "xp": 0,
            "level": 1,
            "last_daily": 0,
            "inventory": {"weapons": [], "animals": []}
        }
        changed = False
        for key, default_value in default_keys.items():
            if key not in db[uid]:
                db[uid][key] = default_value
                changed = True
        if changed:
            save_db(db)
            
    return db[uid]

def update_user(user_id, key, value, mode="set"):
    # 1. KHỞI TẠO BIẾN NGAY TỪ ĐẦU
    is_up = False 
    
    get_user(user_id)
    db = load_db()
    uid = str(user_id)
    
    if mode == "add":
        db[uid][key] += value
    else:
        db[uid][key] = value
        
    save_db(db)
    
    # Lấy level hiện tại
    lvl = db[uid].get("level", 1) 
    
    # 2. TRẢ VỀ BIẾN ĐÃ ĐƯỢC KHỞI TẠO
    return is_up, lvl

# --- SỰ KIỆN TỰ ĐỘNG CÀY XP & CỘNG TIỀN KHI LÊN CẤP ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    user_data = get_user(message.author.id)
    xp_gain = random.randint(1, 5)
    new_xp = user_data["xp"] + xp_gain
    current_lvl = user_data["level"]
    
    xp_needed = current_lvl * 100
    if new_xp >= xp_needed:
        new_xp -= xp_needed
        current_lvl += 1
        
        update_user(message.author.id, "level", current_lvl)
        level_up_reward = current_lvl * 10000
        update_user(message.author.id, "balance", level_up_reward, mode="add")
        
        await message.channel.send(
            f"🎉 Chúc mừng **{message.author.name}** đã thăng cấp lên **Level {current_lvl}**!\n"
            f"🎁 Bạn nhận được phần thưởng độc quyền: **+{level_up_reward:,}** xu đã được cộng vào ví!"
        )
        
    update_user(message.author.id, "xp", new_xp)
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"🎰 SÒNG BÀI ONLINE: Bot {bot.user} đã sẵn sàng hoạt động mượt mà!")

# --- [1] LỆNH ADMIN ĐỘC QUYỀN: BƠM TIỀN ---
@bot.command(name="add")
async def add_money(ctx, member: discord.Member = None, amount: int = None):
    if ctx.author.id != OWNER_ID:
        await ctx.send("❌ Bạn không có quyền hạn Nhà Cái tối cao để thực hiện lệnh này!")
        return
    if not member or not amount:
        await ctx.send("❌ Cú pháp: `cgk add @tên_user <số_tiền>`")
        return
    update_user(member.id, "balance", amount, mode="add")
    await ctx.send(f"👑 **Nhà Cái Tối Cao** đã bơm **+{amount:,}** xu vào ví của {member.mention}!")
    
def check_level_up(uid):
    db = load_db()
    uid = str(uid)
    user = db[uid]
    needed_xp = 100 * (user['level'] ** 2) # Độ khó tăng dần
    
    if user['xp'] >= needed_xp:
        user['level'] += 1
        user['xp'] = 0
        save_db(db)
        return True, user['level']
    return False, user['level']

# --- [2] LỆNH XEM SỐ DƯ & LEVEL ---
@bot.command(name="cash")
async def check_cash(ctx):
    u = get_user(ctx.author.id)
    await ctx.send(f"💳 **{ctx.author.name}** | 💰 Số dư: **{u['balance']:,}** xu | 📊 Level: **{u['level']}** ({u['xp']}/{u['level']*100} XP)")

# --- [3] LỆNH ĐIỂM DANH HÀNG NGÀY ---
@bot.command(name="daily")
async def daily_claim(ctx):
    u = get_user(ctx.author.id)
    now = time.time()
    if now - u["last_daily"] < 86400:
        rem = 86400 - (now - u["last_daily"])
        await ctx.send(f"⏳ Bạn đã điểm danh rồi. Hãy quay lại sau **{int(rem//3600)} giờ {int((rem%3600)//60)} phút**!")
        return
    update_user(ctx.author.id, "balance", 5000, mode="add")
    update_user(ctx.author.id, "last_daily", now)
    await ctx.send(f"🎁 **{ctx.author.name}** vừa nhận thành công **5,000** xu quà điểm danh ngày!")

# --- [4] LỆNH TUNG XU (COINFLIP) ---
@bot.command(name="cf")
async def coinflip(ctx, amount: str = None, choice: str = None):
    if not amount or not choice:
        await ctx.send("❌ Cú pháp: `cgk cf <số_tiền/all> <heads/tails>`")
        return
        
    u = get_user(ctx.author.id)
    if amount.lower() == "all":
        bet = u["balance"]
    else:
        try:
            bet = int(amount)
        except ValueError:
            await ctx.send("❌ Số tiền cược không hợp lệ!")
            return

    if bet <= 0 or bet > u["balance"]:
        await ctx.send("❌ Tiền cược không hợp lệ hoặc số dư không đủ!")
        return
        
    choice = choice.lower()
    if choice not in ["heads", "tails", "h", "t", "sấp", "ngửa"]:
        await ctx.send("❌ Vui lòng chọn đúng `heads` hoặc `tails`.")
        return
        
    user_choice = "heads" if choice in ["heads", "h", "sấp"] else "tails"
    
    msg = await ctx.send(
        f"**{ctx.author.name}** spent **{bet:,}** 💵 and chose **{user_choice}**!\n"
        f"The coin spins... 🔄"
    )
    
    await asyncio.sleep(1.0)
    
    result = random.choice(["heads", "tails"])
    res_emoji = "🟢" if result == "heads" else "🟡"
    
    if user_choice == result:
        update_user(ctx.author.id, "balance", bet, mode="add")
        await msg.edit(content=
            f"**{ctx.author.name}** spent **{bet:,}** 💵 and chose **{user_choice}**!\n"
            f"The coin spins... {res_emoji} {result}!\n"
            f"You won {bet:,}!"
        )
    else:
        update_user(ctx.author.id, "balance", -bet, mode="add")
        await msg.edit(content=
            f"**{ctx.author.name}** spent **{bet:,}** 💵 and chose **{user_choice}**!\n"
            f"The coin spins... {res_emoji} {result}!\n"
            f"You lost it all... :c"
        )

# --- [5] LỆNH QUAY HŨ (SLOTS) - CHỈ TRÁI CÂY VÀ KIM CƯƠNG NGUYÊN BẢN ---
@bot.command(name="s")
async def slots(ctx, amount: str = None):
    if not amount:
        await ctx.send("❌ Cú pháp: `cgk s <số_tiền/all>`")
        return
        
    u = get_user(ctx.author.id)
    if amount.lower() == "all":
        bet = u["balance"]
    else:
        try:
            bet = int(amount)
        except ValueError:
            await ctx.send("❌ Số tiền cược không hợp lệ!")
            return

    if bet <= 0 or bet > u["balance"]:
        await ctx.send("❌ Số tiền cược không hợp lệ hoặc số dư không đủ!")
        return

    items = ["🍎", "🍇", "🍊", "🥭", "💎"]
    
    multipliers = {
        "🍎": 1,
        "🍇": 2,
        "🍊": 3,
        "🥭": 4,
        "💎": 15
    }
    
    # --- CẤU HÌNH TỶ LỆ PHẦN TRĂM THEO Ý BẠN ---
    # Các lựa chọn có thể xảy ra
    options = ["LOSE", "🍎", "🍇", "🍊", "🥭", "💎"]
    # Tỷ lệ phần trăm tương ứng (Tổng = 100)
    weights = [40, 25, 15, 10, 7, 3]
    
    # Bot quay chọn ngẫu nhiên 1 kết quả dựa trên tỷ lệ trên
    final_outcome = random.choices(options, weights=weights, k=1)[0]
    
    if final_outcome != "LOSE":
        # THẮNG: Cả 3 ô đều ra vật phẩm trúng giải
        winning_item = final_outcome
        r1 = r2 = r3 = winning_item
        
        mul = multipliers[winning_item]
        win_amount = bet * mul
        update_user(ctx.author.id, "balance", win_amount, mode="add")
        
        if winning_item == "💎":
            result_msg = f"and won {win_amount:,} 🎉 🔥 NỔ HŨ THẮNG LỚN X15! 🔥 🎉"
        else:
            result_msg = f"and won {win_amount:,} (Trúng 3 {winning_item} x{mul}) 🥳"
    else:
        # THUA: Ra 3 cái khác nhau (Tỷ lệ 40%)
        # Lấy mẫu ngẫu nhiên 3 vật phẩm khác nhau hoàn toàn từ danh sách
        r1, r2, r3 = random.sample(items, 3)
        update_user(ctx.author.id, "balance", -bet, mode="add")
        result_msg = f"and lost {bet:,}"
        
    # --- HIỆU ỨNG QUAY QUAY CHUYÊN NGHIỆP ---
    msg = await ctx.send(f"    ___SLOTS___\n  | 🔄 | 🔄 | 🔄 | cgk bet {bet:,}")

    # Chạy vòng lặp để tạo hiệu ứng quay 4 lần
    for i in range(4):
        await asyncio.sleep(0.4)
        # Random các biểu tượng trong lúc quay
        s1, s2, s3 = random.choice(items), random.choice(items), random.choice(items)
        await msg.edit(content=f"    ___SLOTS___\n  | {s1} | {s2} | {s3} | cgk bet {bet:,}")

    # Hiển thị kết quả cuối cùng (kết quả đã tính toán từ trước)
    await asyncio.sleep(0.4)
    await msg.edit(content=
        f"    ___SLOTS___\n"
        f"  | {r1} | {r2} | {r3} | cgk bet {bet:,} {result_msg}"
    )

# --- [6] XÌ DÁCH (BLACKJACK) ---
def get_card():
    return f"{random.choice(['♥️','♦️','♣️','♠️'])}{random.choice(['2','3','4','5','6','7','8','9','10','J','Q','K','A'])}"

def calc_hand(hand):
    val, aces = 0, 0
    for card in hand:
        c = card[2:]
        if c in ['J', 'Q', 'K']: val += 10
        elif c == 'A': aces += 1; val += 11
        else: val += int(c)
    while val > 21 and aces: val -= 10; aces -= 1
    return val

class BJView(discord.ui.View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=45)
        self.ctx = ctx
        self.bet = bet
        self.p = [get_card(), get_card()]
        self.d = [get_card(), get_card()]

    def make_embed(self, final=False):
        emb = discord.Embed(title="🃏 SÒNG BÀI BLACKJACK CGK", color=0x2f3136)
        emb.add_field(name=f"🤖 Nhà cái (" + (str(calc_hand(self.d)) if final else "??") + ")", value=" ".join(self.d) if final else f"{self.d[0]} 🎴", inline=False)
        emb.add_field(name=f"🧑 Bạn ({calc_hand(self.p)})", value=" ".join(self.p), inline=False)
        emb.set_footer(text=f"Tiền cược: {self.bet:,} xu")
        return emb

    @discord.ui.button(label="Bốc Bài (Hit)", style=discord.ButtonStyle.green, emoji="➕")
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id: return
        self.p.append(get_card())
        if calc_hand(self.p) > 21:
            update_user(self.ctx.author.id, "balance", -self.bet, mode="add")
            self.clear_items()
            await interaction.response.edit_message(embed=self.make_embed(True), content="💥 **Bạn đã Quắc (Vượt quá 21 điểm)! Nhà cái ăn trọn.**", view=self)
            self.stop()
        else:
            await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="Dằn Bài (Stand)", style=discord.ButtonStyle.red, emoji="🛑")
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id: return
        self.clear_items()
        
        await interaction.response.edit_message(content="🤖 **HÀNH ĐỘNG: LẬT MỞ LÁ BÀI CỦA NHÀ CÁI...**", view=self)
        await asyncio.sleep(0.7)
        await interaction.message.edit(embed=self.make_embed(True))
        await asyncio.sleep(0.7)
        
        while calc_hand(self.d) < 17:
            self.d.append(get_card())
            await interaction.message.edit(embed=self.make_embed(True), content="🤖 *Nhà cái đang rút thêm bài...* ➕")
            await asyncio.sleep(0.8)
            
        p, d = calc_hand(self.p), calc_hand(self.d)
        if d > 21 or p > d:
            update_user(self.ctx.author.id, "balance", self.bet, mode="add")
            msg = f"🏆 **Chúc mừng bạn thắng cuộc! Nhận được +{self.bet:,} xu.**"
        elif p < d:
            update_user(self.ctx.author.id, "balance", -self.bet, mode="add")
            msg = f"💸 **Nhà cái điểm cao hơn! Bạn mất -{self.bet:,} xu.**"
        else:
            msg = "🤝 **Hòa bài! Số tiền cược được hoàn lại.**"
            
        await interaction.message.edit(embed=self.make_embed(True), content=msg, view=self)
        self.stop()

@bot.command(name="bj")
async def blackjack_cmd(ctx, amount: str = None):
    if not amount: 
        return await ctx.send("❌ Cú pháp: `cgk bj <số_tiền/all>`")
        
    u = get_user(ctx.author.id)
    if amount.lower() == "all":
        bet = u["balance"]
    else:
        try:
            bet = int(amount)
        except ValueError:
            await ctx.send("❌ Số tiền cược không hợp lệ!")
            return

    if bet <= 0 or bet > u["balance"]: 
        return await ctx.send("❌ Số tiền cược không hợp lệ hoặc ví của bạn không đủ xu!")
        
    view = BJView(ctx, bet)
    await ctx.send(embed=view.make_embed(), view=view)
    
# --- [7] TÀI XỈU ---
@bot.command(name="tx")
async def taixiu(ctx, amount: str, choice: str):
    u = get_user(ctx.author.id)
    try:
        bet = u["balance"] if amount.lower() == "all" else int(amount)
        if bet <= 0 or bet > u["balance"]: raise ValueError
    except: return await ctx.send("❌ Cú pháp: `cgk tx <số_tiền> <t/x>`")
    
    user_choice = "tai" if choice.lower() in ["t", "tai"] else "xiu"
    
    # 1. Gửi tin nhắn khởi tạo
    msg = await ctx.send("🎲 **Đang lắc xúc xắc...** 🎲")
    
    # 2. Vòng lặp hiệu ứng lắc (hiển thị số ngẫu nhiên 3 lần)
    for _ in range(3):
        await asyncio.sleep(0.4)
        await msg.edit(content=f"🎲 **Đang lắc...** `[{random.randint(1,6)}] [{random.randint(1,6)}] [{random.randint(1,6)}]`")
    
    # 3. Kết quả thật
    d1, d2, d3 = random.randint(1,6), random.randint(1,6), random.randint(1,6)
    total = d1 + d2 + d3
    res = "tai" if total >= 11 else "xiu"
    
    # Kiểm tra nổ hũ (1-1-1 đến 6-6-6)
    is_jackpot = (d1 == d2 == d3)
    
    if user_choice == res:
        win_amt = bet * 10 if is_jackpot else bet
        update_user(ctx.author.id, "balance", win_amt, mode="add")
        jackpot_text = "🎉 **NỔ HŨ X10!** " if is_jackpot else "🎉 **Thắng!** "
        await msg.edit(content=f"🎲 Kết quả: `[{d1}] [{d2}] [{d3}]` (Tổng: {total} - {res.upper()})\n{jackpot_text} Bạn nhận được {win_amt:,} xu.")
    else:
        update_user(ctx.author.id, "balance", -bet, mode="add")
        await msg.edit(content=f"🎲 Kết quả: `[{d1}] [{d2}] [{d3}]` (Tổng: {total} - {res.upper()})\n💸 **Thua!** Bạn mất {bet:,} xu.")
        
        
# --- [8] CHẲN LẺ ---  
@bot.command(name="cl")
async def chanle(ctx, amount: str, choice: str):
    u = get_user(ctx.author.id)
    try:
        bet = u["balance"] if amount.lower() == "all" else int(amount)
        if bet <= 0 or bet > u["balance"]: raise ValueError
    except: return await ctx.send("❌ Cú pháp: `cgk cl <số_tiền> <c/l>`")
    
    user_choice = "chan" if choice.lower() in ["c", "chan"] else "le"
    
    # 1. Gửi tin nhắn khởi tạo
    msg = await ctx.send("🎲 **Đang tung xúc xắc...** 🎲")
    
    # 2. Vòng lặp hiệu ứng lắc
    for _ in range(3):
        await asyncio.sleep(0.4)
        await msg.edit(content=f"🎲 **Đang tung...** `[{random.randint(1,6)}] [{random.randint(1,6)}] [{random.randint(1,6)}]`")
        
    # 3. Kết quả thật
    d1, d2, d3 = random.randint(1,6), random.randint(1,6), random.randint(1,6)
    total = d1 + d2 + d3
    res = "chan" if total % 2 == 0 else "le"
    
    is_jackpot = (d1 == d2 == d3)
    
    if user_choice == res:
        win_amt = bet * 10 if is_jackpot else bet
        update_user(ctx.author.id, "balance", win_amt, mode="add")
        jackpot_text = "🎉 **NỔ HŨ X10!** " if is_jackpot else "🎉 **Thắng!** "
        await msg.edit(content=f"🎲 Kết quả: `[{d1}] [{d2}] [{d3}]` (Tổng: {total} - {res.upper()})\n{jackpot_text} Bạn nhận được {win_amt:,} xu.")
    else:
        update_user(ctx.author.id, "balance", -bet, mode="add")
        await msg.edit(content=f"🎲 Kết quả: `[{d1}] [{d2}] [{d3}]` (Tổng: {total} - {res.upper()})\n💸 **Thua!** Bạn mất {bet:,} xu.")
        

# --- LỆNH BÀI CÀO (cào) ---
class CaoView(ui.View):
    def __init__(self, ctx, bet, deck):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bet = bet
        self.deck = deck
        self.player_hand = []
        self.dealer_hand = [self.deck.pop(), self.deck.pop(), self.deck.pop()]

    @ui.button(label="Rút lá bài", style=ButtonStyle.primary)
    async def draw(self, interaction: discord.Interaction, button: ui.Button):
        card = self.deck.pop()
        self.player_hand.append(card)
        
        if len(self.player_hand) < 3:
            content = f"🃏 Bạn đã rút: `{' '.join(self.player_hand)}`\nTiếp tục bấm nút để bốc thêm!"
            await interaction.response.edit_message(content=content, view=self)
        else:
            button.disabled = True
            p_score = self.calculate_score(self.player_hand)
            d_score = self.calculate_score(self.dealer_hand)
            
            # --- TÍNH TOÁN VÀ GHI SỐ TIỀN THẮNG/THUA ---
            if p_score > d_score:
                update_user(self.ctx.author.id, "balance", self.bet, mode="add")
                res = f"🎉 **Thắng!** Bạn nhận được **{self.bet:,} xu**"
            elif p_score < d_score:
                update_user(self.ctx.author.id, "balance", -self.bet, mode="add")
                res = f"💸 **Thua!** Bạn mất **{self.bet:,} xu**"
            else:
                res = f"🤝 **Hòa!** Không mất xu nào."
                
            final_content = (f"🃏 Bài bạn: `{' '.join(self.player_hand)}` (Điểm: **{p_score}**)\n"
                             f"🃏 Nhà cái: `{' '.join(self.dealer_hand)}` (Điểm: **{d_score}**)\n"
                             f"{res}\n💰 Số dư hiện tại: **{get_user(self.ctx.author.id)['balance']:,} xu**")
            
            await interaction.response.edit_message(content=final_content, view=self)

    def calculate_score(self, hand):
        score = 0
        for card in hand:
            rank = card[:-1]
            if rank in ['J', 'Q', 'K']: score += 10
            elif rank == 'A': score += 1
            else: score += int(rank)
        return score % 10

# Lệnh gọi game
@bot.command(name="cao")
async def baicao(ctx, amount: str):
    u = get_user(ctx.author.id)
    try:
        bet = u["balance"] if amount.lower() == "all" else int(amount)
        if bet <= 0 or bet > u["balance"]: raise ValueError
    except: return await ctx.send("❌ Cú pháp: `cgk cao <số_tiền>`")
    
    ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    suits = ['♠', '♣', '♦', '♥']
    deck = [r + s for r in ranks for s in suits]
    random.shuffle(deck)
    
    view = CaoView(ctx, bet, deck)
    await ctx.send("🃏 Bấm nút để bốc bài:", view=view)
    
    # --- BẦU CUA ---
class BauCuaSelect(ui.Select):
    def __init__(self):
        options = [SelectOption(label=s, value=s) for s in ["Bầu", "Cua", "Tôm", "Cá", "Gà", "Nai"]]
        super().__init__(placeholder="Chọn 1 linh vật để đặt...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.ctx.author.id:
            return await interaction.response.send_message("❌ Không phải ván của bạn!", ephemeral=True)
            
        self.view.selected_symbol = self.values[0]
        self.disabled = True # KHÓA MENU SAU KHI CHỌN
        
        # CẬP NHẬT LẠI TIN NHẮN GỐC ĐỂ HIỂN THỊ LỰA CHỌN
        new_content = f"🎲 **Bầu Cua Tôm Cá**\nĐã chốt đặt cửa: **{self.values[0]}**\nBấm nút Lắc để xem kết quả!"
        await interaction.response.edit_message(content=new_content, view=self.view)

class BauCuaView(ui.View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bet = bet
        self.selected_symbol = None
        self.add_item(BauCuaSelect())

    # --- HÀM KIỂM TRA QUYỀN ---
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Đây không phải ván của bạn!", ephemeral=True)
            return False
        return True

    @ui.button(label="Lắc Xúc Xắc", style=ButtonStyle.success)
    async def roll(self, interaction: discord.Interaction, button: ui.Button):
        # Kiểm tra nếu chưa chọn thì chặn lại
        if not self.selected_symbol:
            return await interaction.response.send_message("❌ Hãy chọn linh vật trước đã!", ephemeral=True)
            
        button.disabled = True
        
        # CHUYỂN SANG DÙNG follow-up để tránh lỗi trùng lặp
        await interaction.response.defer() # Báo cho Discord biết bot đang xử lý
        
        symbols = ["Bầu", "Cua", "Tôm", "Cá", "Gà", "Nai"]
        results = [random.choice(symbols) for _ in range(3)]
        hit_count = results.count(self.selected_symbol)
        
        if hit_count > 0:
            win_amt = self.bet * hit_count
            update_user(self.ctx.author.id, "balance", win_amt, mode="add")
            res = f"🎉 **Chúc mừng!** Ra {hit_count} con {self.selected_symbol}. Thắng **{win_amt:,} xu**"
        else:
            update_user(self.ctx.author.id, "balance", -self.bet, mode="add")
            res = f"💸 **Chia buồn!** Không có {self.selected_symbol}. Bạn mất **{self.bet:,} xu**"
            
        final_content = (f"🎲 Kết quả: **{', '.join(results)}**\n"
                         f"{res}\n💰 Số dư: **{get_user(self.ctx.author.id)['balance']:,} xu**")
        
        # Dùng edit_original_response để cập nhật tin nhắn hiện có mà không gây lỗi
        await interaction.edit_original_response(content=final_content, view=self)


@bot.command(name="bc")
async def baucua(ctx, amount: str):
    u = get_user(ctx.author.id)
    try:
        bet = int(amount)
        if bet <= 0 or bet > u["balance"]: raise ValueError
    except: return await ctx.send("❌ Cú pháp: `cgk bau <số_tiền>`")
    
    view = BauCuaView(ctx, bet)
    await ctx.send("🎲 **Bầu Cua Tôm Cá** - Chọn cửa và bấm lắc:", view=view)
    
# --- [9] HỆ THỐNG MỞ HÒM VŨ KHÍ (CRATE) ---
@bot.command(name="crate")
async def open_crate(ctx):
    u = get_user(ctx.author.id)
    if u["balance"] < 10000: 
        return await ctx.send("❌ Bạn cần **10,000** xu để mua và mở Crate vũ khí!")
        
    update_user(ctx.author.id, "balance", -10000, mode="add")
    
    rewards = ["⚔️ Kiếm Rỉ Sét (Thường)", "🏹 Cung Gỗ (Thường)", "🛡️ Khiên Thép (Hiếm)", "🪄 Trượng Ma Thuật (Epic)", "🔱 Rìu Thần Thần Thoại (Legendary)"]
    weights = [50, 30, 14, 5, 1]
    result = random.choices(rewards, weights=weights, k=1)[0]
    
    db = load_db()
    uid = str(ctx.author.id)
    if "weapons" not in db[uid]["inventory"]:
        db[uid]["inventory"]["weapons"] = []
    db[uid]["inventory"]["weapons"].append(result)
    save_db(db)
    
    await ctx.send(f"📦 **{ctx.author.name}** đã chi 10,000 xu khui hòm vũ khí và nhận được: **{result}**!")

# ---BCR---
@bot.command(name="bcr", aliases=["baccarat", "bac"])
async def bcr(ctx, *args):
    # --- BƯỚC 1: KIỂM TRA CÚ PHÁP ĐẦU VÀO TỰ ĐỘNG ---
    # args sẽ gom toàn bộ chữ người chơi gõ thành 1 danh sách.
    # Nếu người chơi không gõ gì, hoặc gõ lẻ từ (VD: 1000 con 500) -> Báo lỗi
    if not args or len(args) % 2 != 0:
        msg = (
            "❌ **Cú pháp lệnh không đúng!**\n"
            "👉 **Cách cược:** `cgk bcr <tiền> <cửa> <tiền> <cửa>...`\n"
            "*(Bạn có thể cược bao nhiêu cửa cùng lúc tùy thích)*\n\n"
            "**Các cửa cược hợp lệ:** `con`, `cai`, `hoa`, `condoi`, `caidoi`\n"
            "Ví dụ 1 cửa: `cgk bcr 5000 con`\n"
            "Ví dụ 3 cửa: `cgk bcr 1000 con 1000 hoa 1000 condoi`"
        )
        await ctx.send(msg)
        return

    u = get_user(ctx.author.id)
    total_bet = 0
    bets = {} # Lưu danh sách các cửa và tiền cược

    # Hàm chuẩn hóa tên cửa
    def clean_choice(c):
        c = c.lower()
        if c in ["cái", "cai", "b"]: return "cai"
        if c in ["hòa", "hoa", "t"]: return "hoa"
        if c in ["con", "p"]: return "con"
        if c in ["condôi", "condoi"]: return "condoi"
        if c in ["cáidôi", "caidôi", "caidoi"]: return "caidoi"
        return None

    # Tự động quét từng cặp (Tiền - Cửa) mà người chơi nhập vào
    for i in range(0, len(args), 2):
        amt_str = args[i]
        choice_str = args[i+1]
        
        c = clean_choice(choice_str)
        if not c:
            return await ctx.send(f"❌ Cửa cược `{choice_str}` không hợp lệ!")
            
        if c in bets:
            return await ctx.send(f"❌ Bạn không thể đặt trùng cửa **{c.upper()}** 2 lần trong một ván!")
            
        if amt_str.lower() == "all":
            bet_amt = u["balance"]
        else:
            try: bet_amt = int(amt_str)
            except ValueError: return await ctx.send(f"❌ Số tiền `{amt_str}` không hợp lệ!")
            
        if bet_amt <= 0: return await ctx.send("❌ Số tiền cược phải lớn hơn 0!")
        
        bets[c] = bet_amt
        total_bet += bet_amt

    # Kiểm tra tổng tiền cược tất cả các cửa có đủ không
    if total_bet > u["balance"]:
        return await ctx.send(f"❌ Không đủ tiền! Tổng tiền bạn đang cược là **{total_bet:,} xu**, nhưng bạn chỉ có **{u['balance']:,} xu**.")

    # Trừ tổng tiền cược ngay từ đầu ván
    update_user(ctx.author.id, "balance", -total_bet, mode="add")

    # --- BƯỚC 2: LOGIC BÀI TÂY (CHIA TRONG RAM) ---
    def get_card():
        suits = ["♠", "♣", "♥", "♦"]
        ranks = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
        r = random.choice(ranks)
        s = random.choice(suits)
        val = 0 if r in ["10", "J", "Q", "K"] else (1 if r == "A" else int(r))
        return f"{r}{s}", val, r

    p1, p1_v, p1_r = get_card()
    p2, p2_v, p2_r = get_card()
    b1, b1_v, b1_r = get_card()
    b2, b2_v, b2_r = get_card()

    is_player_pair = (p1_r == p2_r)
    is_banker_pair = (b1_r == b2_r)

    p_score_2 = (p1_v + p2_v) % 10
    b_score_2 = (b1_v + b2_v) % 10

    p_cards = [p1, p2]
    b_cards = [b1, b2]

    has_p3, has_b3 = False, False
    if p_score_2 < 8 and b_score_2 < 8:
        p3_v = -1
        if p_score_2 <= 5:
            p3, p3_v, _ = get_card()
            p_cards.append(p3)
            has_p3 = True

        if b_score_2 <= 2 or (b_score_2 == 3 and p3_v != 8) or \
           (b_score_2 == 4 and p3_v in [2, 3, 4, 5, 6, 7]) or \
           (b_score_2 == 5 and p3_v in [4, 5, 6, 7]) or \
           (b_score_2 == 6 and p3_v in [6, 7]):
            b3, b3_v, _ = get_card()
            b_cards.append(b3)
            has_b3 = True

    p_score_final = sum([0 if c[:-1] in ["10", "J", "Q", "K"] else (1 if c[:-1] == "A" else int(c[:-1])) for c in p_cards]) % 10
    b_score_final = sum([0 if c[:-1] in ["10", "J", "Q", "K"] else (1 if c[:-1] == "A" else int(c[:-1])) for c in b_cards]) % 10

    if p_score_final > b_score_final: main_result = "con"
    elif b_score_final > p_score_final: main_result = "cai"
    else: main_result = "hoa"

    # --- BƯỚC 3: HIỆU ỨNG LẬT BÀI TỪNG LÁ ---
    embed = discord.Embed(title="🃏 CASINO BACCARAT 🃏", color=discord.Color.blue())
    embed.add_field(name="🧑 PLAYER (Con)", value="Bài: ` 🎴 | 🎴 `\nĐiểm: **?**", inline=True)
    embed.add_field(name="🏢 BANKER (Cái)", value="Bài: ` 🎴 | 🎴 `\nĐiểm: **?**", inline=True)
    embed.add_field(name="📊 KẾT QUẢ TRẬN ĐẤU", value=f"Đang xóc và chia bài...", inline=False)
    msg = await ctx.send(embed=embed)

    await asyncio.sleep(0.6)
    embed.set_field_at(0, name="🧑 PLAYER (Con)", value=f"Bài: ` {p1} | 🎴 `\nĐiểm: **?**", inline=True)
    await msg.edit(embed=embed)

    await asyncio.sleep(0.6)
    embed.set_field_at(1, name="🏢 BANKER (Cái)", value=f"Bài: ` {b1} | 🎴 `\nĐiểm: **?**", inline=True)
    await msg.edit(embed=embed)

    await asyncio.sleep(0.6)
    p_pair_str = " *(ĐÔI CON!)*" if is_player_pair else ""
    embed.set_field_at(0, name="🧑 PLAYER (Con)", value=f"Bài: ` {p1} | {p2} `{p_pair_str}\nĐiểm: **{p_score_2}**", inline=True)
    await msg.edit(embed=embed)

    await asyncio.sleep(0.6)
    b_pair_str = " *(ĐÔI CÁI!)*" if is_banker_pair else ""
    embed.set_field_at(1, name="🏢 BANKER (Cái)", value=f"Bài: ` {b1} | {b2} `{b_pair_str}\nĐiểm: **{b_score_2}**", inline=True)
    await msg.edit(embed=embed)

    if has_p3:
        await asyncio.sleep(0.8)
        embed.set_field_at(2, name="📊 KẾT QUẢ TRẬN ĐẤU", value="Player rút lá thứ 3...", inline=False)
        await msg.edit(embed=embed)
        await asyncio.sleep(0.8)
        embed.set_field_at(0, name="🧑 PLAYER (Con)", value=f"Bài: ` {p1} | {p2} | {p3} `{p_pair_str}\nĐiểm: **{p_score_final}**", inline=True)
        await msg.edit(embed=embed)

    if has_b3:
        await asyncio.sleep(0.8)
        embed.set_field_at(2, name="📊 KẾT QUẢ TRẬN ĐẤU", value="Banker rút lá thứ 3...", inline=False)
        await msg.edit(embed=embed)
        await asyncio.sleep(0.8)
        embed.set_field_at(1, name="🏢 BANKER (Cái)", value=f"Bài: ` {b1} | {b2} | {b3} `{b_pair_str}\nĐiểm: **{b_score_final}**", inline=True)
        await msg.edit(embed=embed)

    # --- BƯỚC 4: TÍNH TOÁN KẾT QUẢ ĐA CỬA ---
    await asyncio.sleep(0.5)
    win_money = 0
    detail_msg = []

    # Duyệt qua tất cả các cửa mà người chơi đã đặt
    for door, bet_amt in bets.items():
        is_door_win = False
        mul = 0
        
        if door == "con" and main_result == "con": is_door_win = True; mul = 2
        elif door == "cai" and main_result == "cai": is_door_win = True; mul = 1.95
        elif door == "hoa" and main_result == "hoa": is_door_win = True; mul = 9
        elif door == "condoi" and is_player_pair: is_door_win = True; mul = 12
        elif door == "caidoi" and is_banker_pair: is_door_win = True; mul = 12

        if is_door_win:
            prize = int(bet_amt * mul)
            win_money += prize
            detail_msg.append(f"✅ Thắng cửa **{door.upper()}**: +{prize:,} xu (x{mul})")
        else:
            detail_msg.append(f"❌ Thua cửa **{door.upper()}**: -{bet_amt:,} xu")

    # Xử lý tổng lợi nhuận (Tiền thu về trừ đi tiền vốn)
    net_profit = win_money - total_bet
    if win_money > 0:
        update_user(ctx.author.id, "balance", win_money, mode="add")
        
    if net_profit > 0:
        status_msg = f"🎉 **BẠN ĐÃ LỜI CHUNG CUỘC!** (+{net_profit:,} xu)."
        embed.color = discord.Color.green()
    elif net_profit < 0:
        status_msg = f"💸 **BẠN ĐÃ LỖ CHUNG CUỘC!** ({net_profit:,} xu)."
        embed.color = discord.Color.red()
    else:
        status_msg = "⚖️ **HÒA VỐN!** Không tăng không giảm số dư."
        embed.color = discord.Color.gold()

    is_up, lvl = update_user(ctx.author.id, "xp", 15, mode="add")

    win_doors = [main_result.upper()]
    if is_player_pair: win_doors.append("ĐÔI CON (CONDOI)")
    if is_banker_pair: win_doors.append("ĐÔI CÁI (CAIDOI)")

    # In ra bill chi tiết từng cửa đặt
    history_str = "\n".join(detail_msg)
    embed.set_field_at(2, name="📊 KẾT QUẢ TRẬN ĐẤU", value=f"Cửa xuất hiện: **{', '.join(win_doors)}**\n\n**Chi tiết cược:**\n{history_str}\n\n**Kết luận:** {status_msg}", inline=False)
    
    if is_up:
        embed.set_footer(text=f"🎉 Xuất sắc! Bạn đã thăng cấp lên Level {lvl}!")
        
    await msg.edit(embed=embed)
    
# --- [10] HỆ THỐNG MỞ HÒM THÚ CƯNG (LOOTBOX) ---
@bot.command(name="lootbox")
async def open_lootbox(ctx):
    u = get_user(ctx.author.id)
    if u["balance"] < 25000: 
        return await ctx.send("❌ Bạn cần **25,000** xu để mua Siêu Hòm Lootbox Thú Cưng!")
        
    update_user(ctx.author.id, "balance", -25000, mode="add")
    
    rewards = ["🦊 Cáo Lửa", "🐼 Gấu Trúc Thần Kỳ", "🐉 Rồng Con Thượng Cổ"]
    weights = [70, 25, 5]
    result = random.choices(rewards, weights=weights, k=1)[0]
    
    db = load_db()
    uid = str(ctx.author.id)
    if "animals" not in db[uid]["inventory"]:
        db[uid]["inventory"]["animals"] = []
    db[uid]["inventory"]["animals"].append(result)
    save_db(db)
    
    await ctx.send(f"🧰 **{ctx.author.name}** mở Siêu Hòm Lootbox và nhận được Linh Thú: **{result}**!")

# --- [11] ĐẤU TRƯỜNG SINH TỬ THÚ CƯNG (BATTLE) ---
@bot.command(name="battle")
async def pet_battle(ctx):
    u = get_user(ctx.author.id)
    animals = u["inventory"].get("animals", [])
    if not animals: 
        return await ctx.send("❌ Bạn không có thú cưng nào để tham chiến! Hãy mua và mở hòm `cgk lootbox` trước.")
    
    my_pet = animals[0]
    wild_enemies = ["🐗 Lợn Rừng Hung Dữ", "🐺 Sói Xám Đói Khát", "🦁 Sư Tử Đầu Đàn"]
    enemy = random.choice(wild_enemies)
    
    msg = await ctx.send(f"⚔️ **{my_pet}** của bạn đang gầm gừ lao vào đấu trường tỉ thí với **{enemy}**...")
    await asyncio.sleep(1.5)
    
    win = random.choice([True, False])
    if win:
        reward_money = random.randint(3000, 8000)
        reward_xp = random.randint(50, 100)
        update_user(ctx.author.id, "balance", reward_money, mode="add")
        
        db = load_db()
        db[str(ctx.author.id)]["xp"] += reward_xp
        save_db(db)
        
        await msg.edit(content=f"🏆 **{my_pet}** đã hạ gục hoàn toàn {enemy}!\n🎁 Phần thưởng mang về: **+{reward_money:,} xu** và **+{reward_xp} XP** tích lũy.")
    else:
        await msg.edit(content=f"💀 Trận chiến kết thúc quá thảm khốc! **{my_pet}** đã bại trận trước {enemy} và được đưa về trạm y tế dưỡng thương.")
        
# --- LỆNH QUẢN TRỊ: XÓA TIỀN CỦA NGƯỜI CHƠI ---
@bot.command(name="xoatien")
@commands.has_permissions(administrator=True)
async def xoatien(ctx, member: discord.Member):
    file_path = 'bank.json'
    
    # Đọc dữ liệu
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    user_id = str(member.id)
    
    if user_id in data:
        # Cách sửa: Chỉ gán balance về 0, không gán cả user_id = 0
        if isinstance(data[user_id], dict):
            data[user_id]['balance'] = 0
        else:
            # Trường hợp dữ liệu cũ của bạn chỉ là số đơn thuần
            data[user_id] = {"balance": 0, "level": 1, "xp": 0}
            
        # Lưu lại file
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
            
        await ctx.send(f"✅ Đã xóa sạch số dư của {member.mention} về 0.")
    else:
        await ctx.send("❌ Người dùng này chưa có tài khoản trong hệ thống.")

    # Lưu lại file
    with open(file_path, 'w') as f:
        json.dump(data, f)

# 3. LỆNH TỰ XÓA TIỀN CỦA CHÍNH MÌNH
@bot.command(name="resetme")
async def resetme(ctx):
    update_user(ctx.author.id, "balance", 0, mode="set")
    await ctx.send(f"✅ {ctx.author.mention}, bạn đã tự xóa sạch số dư của mình!")
        
# --- LỆNH XEM BẢNG XẾP HẠNG ---
@bot.command(name="top")
async def top(ctx):
    db = load_db()
    # Chuyển đổi database thành danh sách [ (id, số_tiền), ... ]
    user_list = []
    for uid, data in db.items():
        if isinstance(data, dict) and "balance" in data:
            user_list.append((uid, data["balance"]))
    
    # Sắp xếp theo số tiền giảm dần
    user_list.sort(key=lambda x: x[1], reverse=True)
    
    # Lấy top 5
    top_5 = user_list[:5]
    
    msg = "🏆 **BẢNG XẾP HẠNG GIÀU CÓ** 🏆\n"
    for i, (uid, balance) in enumerate(top_5):
        # Lấy tên người dùng từ ID
        user = await bot.fetch_user(int(uid))
        msg += f"{i+1}. **{user.name}**: {balance:,} xu\n"
        
    await ctx.send(msg)
    
# ---CHO TIỀN---
@bot.command(name="give")
async def give(ctx, member: discord.Member, amount: int):
    # 1. Kiểm tra số tiền hợp lệ
    if amount <= 0:
        return await ctx.send("❌ Số tiền tặng phải lớn hơn 0!")
    
    if member.id == ctx.author.id:
        return await ctx.send("❌ Bạn không thể tự tặng tiền cho chính mình!")

    # 2. Đọc dữ liệu
    db = load_db()
    sender_id = str(ctx.author.id)
    receiver_id = str(member.id)
    
    # Đảm bảo sender có tài khoản
    if sender_id not in db: db[sender_id] = {"balance": 0}
    # Đảm bảo receiver có tài khoản
    if receiver_id not in db: db[receiver_id] = {"balance": 0}

    # 3. Kiểm tra số dư người gửi
    if db[sender_id]["balance"] < amount:
        return await ctx.send(f"❌ Bạn không đủ tiền! Bạn chỉ có **{db[sender_id]['balance']:,} xu**.")

    # 4. Thực hiện giao dịch (Trừ người gửi - Cộng người nhận)
    db[sender_id]["balance"] -= amount
    db[receiver_id]["balance"] += amount
    save_db(db)

    await ctx.send(f"✅ {ctx.author.mention} đã tặng **{amount:,} xu** cho {member.mention}!")
 
#--- DSGAME ---
@bot.command(name="dsgame", aliases=["help", "menu", "hd"])
async def dsgame(ctx):
    # Tạo bảng Embed giao diện chính
    embed = discord.Embed(
        title="🎰 TỔNG HỢP LỆNH HỆ THỐNG CASINO 🎰",
        description=f"Xin chào {ctx.author.mention}! Dưới đây là toàn bộ danh sách trò chơi và tính năng bạn có thể trải nghiệm.",
        color=discord.Color.gold()
    )
    
    if bot.user.avatar:
        embed.set_thumbnail(url=bot.user.avatar.url)

    # 1. KHU VỰC TÀI CHÍNH & CÁ NHÂN
    economy_cmd = (
        "💳 `cgk cash` - Xem số dư tài khoản, Level và XP hiện tại.\n"
        "🎁 `cgk daily` - Điểm danh nhận xu và phần thưởng mỗi ngày.\n"
        "💸 `cgk give @người_chơi <số_tiền>` - Chuyển tiền cho người khác."
    )
    embed.add_field(name="🏦 HỆ THỐNG TÀI CHÍNH", value=economy_cmd, inline=False)

    # 2. KHU VỰC MINI-GAMES (CÁ CƯỢC NHANH)
    minigame_cmd = (
        "🪙 `cgk cf <tiền> <tài/xỉu>` - Coinflip (Tung đồng xu may rủi).\n"
        "🎰 `cgk s <tiền/all>` - Quay Slots hoa quả nổ hũ x15.\n"
        "🎲 `cgk tx <tiền> <tài/xỉu>` - Đổ xúc xắc Tài Xỉu.\n"
        "🔢 `cgk cl <tiền> <chẵn/lẻ>` - Cược Chẵn Lẻ cơ bản.\n"
        "🦀 `cgk bc <tiền> <vật_phẩm>` - Lắc Bầu Cua tôm cá."
    )
    embed.add_field(name="🎲 MINI GAMES GIẢI TRÍ", value=minigame_cmd, inline=False)

    # 3. KHU VỰC GAME BÀI (CARD GAMES) & BACCARAT CHI TIẾT
    card_cmd = (
        "🃏 `cgk bj <tiền>` - Chơi Xì Dách (Blackjack) đọ trí với nhà cái.\n"
        "🎴 `cgk cao <tiền>` - Chơi Bài Cào 3 lá.\n\n"
        "**👑 BACCARAT (LỆNH: `cgk bcr`)**\n"
        "Các cửa: `con` (x2), `cai` (x1.95), `hoa` (x9), `condoi` (x12), `caidoi` (x12).\n"
        "👉 **Cách 1 (Cược Đơn):** `cgk bcr <tiền> <cửa>`\n"
        "*(VD: `cgk bcr 5000 con` - Đặt 5K vào cửa Player)*\n"
        "👉 **Cách 2 (Cược Kép):** `cgk bcr <tiền_1> <cửa_1> <tiền_2> <cửa_2>`\n"
        "*(VD: `cgk bcr 5000 con 1000 condoi` - Đặt 5K cửa Player & 1K cửa Đôi Con)*"
    )
    embed.add_field(name="♠️ CASINO GAME BÀI", value=card_cmd, inline=False)

    # 4. KHU VỰC VẬT PHẨM & TƯƠNG TÁC NGƯỜI CHƠI (PVP)
    pvp_cmd = (
        "📦 `cgk crate` - Mở rương phần thưởng (Cần có key/tiền để mở lấy ngẫu nhiên XP, Xu).\n"
        "🔮 `cgk lootbox` - Mở hộp quà bí ẩn (Tỉ lệ ra đồ hiếm hoặc trúng thưởng lớn cao hơn crate).\n"
        "⚔️ `cgk battle @người_chơi <tiền>` - Thách đấu tay đôi (PvP). Cả 2 cùng cược tiền, hệ thống sẽ random người chiến thắng ăn trọn tiền cược!"
    )
    embed.add_field(name="🔥 HỆ THỐNG VẬT PHẨM & THÁCH ĐẤU", value=pvp_cmd, inline=False)

    # 5. KHU VỰC LỆNH ADMIN (Chỉ Admin mới thấy)
    if ctx.author.guild_permissions.administrator:
        admin_cmd = (
            "⚙️ `cgk add @người_chơi <số_tiền>` - Bơm thêm tiền cho người chơi.\n"
            "*(Chỉ Quản trị viên mới nhìn thấy mục này)*"
        )
        embed.add_field(name="🛡️ LỆNH QUẢN TRỊ VIÊN", value=admin_cmd, inline=False)

    # Footer trang trí
    embed.set_footer(
        text=f"Người gọi lệnh: {ctx.author.name} • Tiền tố bot: cgk", 
        icon_url=ctx.author.avatar.url if ctx.author.avatar else None
    )

    await ctx.send(embed=embed)
 
app = Flask('')

@app.route('/')
def home():
    return "Bot đang chạy 24/7!"

def run():
    # Lấy cổng do Render cấp tự động, nếu không có mới dùng 8080
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
    
# --- KÍCH HOẠT HỆ THỐNG SÒNG BÀI CASINO ---
keep_alive()
bot.run(token)