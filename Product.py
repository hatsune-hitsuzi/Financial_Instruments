import requests
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, FuncFormatter
from datetime import datetime, timedelta
import sys
from art import text2art

def parse_float(value):
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(',', ''))
    except (ValueError, TypeError):
        return 0.0

def convert_to_expiration_code(date_str):
    month_codes = {
        '01': 'F', '02': 'G', '03': 'H', '04': 'J',
        '05': 'K', '06': 'M', '07': 'N', '08': 'Q',
        '09': 'U', '10': 'V', '11': 'X', '12': 'Z'
    }
    try:
        year = date_str[2:4]
        month = date_str[4:]
        code = month_codes[month] + year
        return code
    except (KeyError, ValueError, IndexError):
        print("输入格式错误，应为形如 '202508' 的年月格式")
        return None

# TODO: 看样子reporttype可能会每日改动导致硬编码请求失效,建议直接去:https://www.cmegroup.com/markets/metals/precious/gold.volume.options.html看看请求就好,有空再更新~
def fetch_option_data(expiration_code):
    """从CME Group获取期权数据"""
    url = 'https://www.cmegroup.com/CmeWS/mvc/Volume/Options/Details'
    params = {
        'productid': '192',
        'tradedate': (datetime.now() - timedelta(days=1)).strftime('%Y%m%d'),
        'expirationcode': expiration_code,
        'reporttype': 'P'
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Referer': 'https://www.cmegroup.com/markets/metals/precious/gold.volume.options.html',
        'Accept': 'application/json'
    }

    response = requests.get(url, params=params, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"请求失败: {response.status_code}")
        return None

def plot_option_comparison(response_data, low_strike, high_strike, raw_date):
    if not response_data:
        print("无有效数据可绘制")
        return

    # 定制颜色设置
    bg_color = '#212F3C'  # 主背景色
    right_panel_color = '#181D29'  # 右侧面板背景色
    bar_color = '#00FF8C'  # 柱状图颜色
    line_color = '#4B7DB0'  # 折线颜色
    text_color = 'white'  # 文字颜色
    grid_color = '#34495E'  # 网格线颜色

    # 数据提取和过滤
    calls_data = []
    puts_data = []

    for month_data in response_data.get('monthData', []):
        for strike_data in month_data.get('strikeData', []):
            try:
                strike = parse_float(strike_data.get('strike'))
                if not (low_strike <= strike <= high_strike):
                    continue

                month_id = strike_data.get('monthID', '')
                if month_id.endswith('-Calls'):
                    calls_data.append({
                        'strike': strike,
                        'change': parse_float(strike_data.get('change')),
                        'volume': parse_float(strike_data.get('totalVolume'))
                    })
                elif month_id.endswith('-Puts'):
                    puts_data.append({
                        'strike': strike,
                        'change': parse_float(strike_data.get('change')),
                        'volume': parse_float(strike_data.get('totalVolume'))
                    })
            except Exception as e:
                print(f"数据处理错误: {e}")
                continue

    # 检查数据
    if not calls_data and not puts_data:
        print("妹有有效数据")
        return

    # 排序数据
    calls_data.sort(key=lambda x: x['strike'])
    puts_data.sort(key=lambda x: x['strike'])

    # 准备绘图数据
    calls_strikes = [x['strike'] for x in calls_data]
    calls_changes = [x['change'] for x in calls_data]
    calls_volumes = [x['volume'] for x in calls_data]

    puts_strikes = [x['strike'] for x in puts_data]
    puts_changes = [x['change'] for x in puts_data]
    puts_volumes = [x['volume'] for x in puts_data]

    # 创建图表
    plt.style.use('dark_background')  # 使用深色背景样式
    fig = plt.figure(figsize=(18, 10), facecolor=bg_color)
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1])
    ax1 = fig.add_subplot(gs[0], facecolor=bg_color)
    ax2 = fig.add_subplot(gs[1], facecolor=right_panel_color, sharey=ax1)

    fig.suptitle('Gold option' + raw_date + 'option chart',
                 fontsize=16, y=0.95, color=text_color)

    # ========== 固定比例尺设置 ==========
    # 纵坐标设置 (行权价)
    y_min, y_max = low_strike, high_strike
    y_major_locator = MultipleLocator(20)  # 每20一个主刻度

    # 横坐标设置 (价格变化) —— 动态范围
    max_change = max(
        max([abs(x) for x in calls_changes], default=0),
        max([abs(x) for x in puts_changes], default=0)
    )
    x_max = max(600, int(max_change * 1.1))  # 至少600，或者自动扩展
    x_major_locator = MultipleLocator(100)

    # ========== Calls图表 (左侧) ==========
    if calls_data:
        # 价格变化柱状图
        bars = ax1.barh(calls_strikes, calls_changes, height=3,
                        color=bar_color, alpha=0.8)
        ax1.axvline(0, color=text_color, linewidth=0.8)

        # 添加数据标签
        for bar in bars:
            width = bar.get_width()
            if abs(width) > 5:  # 只显示变化较大的值
                ax1.text(width, bar.get_y() + bar.get_height() / 2,
                         f'{width:+.1f}',
                         va='center', ha='left' if width > 0 else 'right',
                         fontsize=8, color=text_color)

        # 存粮期权量折线图
        ax1b = ax1.twiny()
        ax1b.plot(calls_volumes, calls_strikes, color=line_color, marker='o',
                  markersize=5, linewidth=2, alpha=0.8, label='stock')

        # 设置坐标轴
        ax1.set_xlim(-x_max, x_max)
        ax1.xaxis.set_major_locator(x_major_locator)
        ax1.set_ylim(y_min, y_max)
        ax1.yaxis.set_major_locator(y_major_locator)
        ax1.grid(True, linestyle=':', alpha=0.3, color=grid_color)

        # 设置标签颜色
        ax1.set_title('Calls', pad=20, fontsize=14, color=text_color)
        ax1.set_xlabel('change', labelpad=10, color=text_color)
        ax1b.set_xlabel('Open position volume', labelpad=10, color=text_color)

        # 设置坐标轴颜色
        ax1.tick_params(axis='x', colors=text_color)
        ax1.tick_params(axis='y', colors=text_color)
        ax1b.tick_params(axis='x', colors=text_color)

        # 设置边框颜色
        for spine in ax1.spines.values():
            spine.set_color(text_color)

    # ========== Puts图表 (右侧) ==========
    if puts_data:
        # 价格变化柱状图
        bars = ax2.barh(puts_strikes, puts_changes, height=3,
                        color=bar_color, alpha=0.8)
        ax2.axvline(0, color=text_color, linewidth=0.8)

        # 添加数据标签
        for bar in bars:
            width = bar.get_width()
            if abs(width) > 5:  # 只显示变化较大的值
                ax2.text(width, bar.get_y() + bar.get_height() / 2,
                         f'{width:+.1f}',
                         va='center', ha='right' if width > 0 else 'left',
                         fontsize=8, color=text_color)

        # 存粮期权量折线图
        ax2b = ax2.twiny()
        ax2b.plot(puts_volumes, puts_strikes, color=line_color, marker='o',
                  markersize=5, linewidth=2, alpha=0.8, label='stock')

        # 设置坐标轴
        ax2.set_xlim(-x_max, x_max)  # 反转x轴
        ax2.xaxis.set_major_locator(x_major_locator)
        ax2.set_ylim(y_min, y_max)
        ax2.yaxis.set_major_locator(y_major_locator)
        ax2.grid(True, linestyle=':', alpha=0.3, color=grid_color)

        # 设置标签颜色
        ax2.set_title('Puts', pad=20, fontsize=14, color=text_color)
        ax2.set_xlabel('change', labelpad=10, color=text_color)
        ax2b.set_xlabel('Open position volume', labelpad=10, color=text_color)

        # 设置坐标轴颜色
        ax2.tick_params(axis='x', colors=text_color)
        ax2.tick_params(axis='y', colors=text_color)
        ax2b.tick_params(axis='x', colors=text_color)

        # 设置边框颜色
        for spine in ax2.spines.values():
            spine.set_color(text_color)

    # 通用设置
    ax1.set_ylabel('price', color=text_color)

    # 调整布局
    plt.tight_layout()
    plt.subplots_adjust(top=0.9)

    # 保存图表
    filename = f"gold_options_{datetime.now().strftime('%Y%m%d')}.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor=bg_color)
    print(f"图表已保存为: {filename}")

    plt.show()


def banner():
    print("小羊黄金期权分析")
    print("Data Source: CME Chicago Mercantile Exchange,国内用户请使用魔法")
    print("Contact")
    print("GitHub: https://github.com/hatsune-hitsuzi/Financial_Instruments")
    print("Mail: 534622443abc@gmail.com")
    print("=" * 40)

def get_float(prompt):
    while True:
        try:
            return float(input(prompt).strip())
        except ValueError:
            print("⚠️ 输入无效，请输入数字！")

def main():
    banner()
    low_strike = get_float("请输入最低行权价 XAU/USD：")
    high_strike = get_float("请输入最高行权价 XAU/USD：")
    raw_date = input("请输入期权到期年月 (格式如 202508)：").strip()
    expiration_code = convert_to_expiration_code(raw_date)
    if not expiration_code:
        print("⚠️ 到期年月格式不正确，退出。")
        sys.exit(1)

    print("\n正在获取数据…请稍候...")
    option_data = fetch_option_data(expiration_code)
    if not option_data:
        print("❌ 无法获取数据，请检查网络或命令调用是否正确。")
        sys.exit(1)

    plot_option_comparison(option_data, low_strike, high_strike, raw_date)
    print("\n" + "=" * 40)
    print("© 2025 hatsune‑hitsuzi. All rights reserved.")

if __name__ == "__main__":
    main()