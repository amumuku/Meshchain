import aiohttp
import asyncio
import aiofiles
import logging
import time
import datetime


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 设置默认请求头
headers = {
    'Content-Type': 'application/json',
}

# coday 函数
async def coday(url, method, headers, payload_data=None, proxy=None):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=headers, json=payload_data, proxy=proxy) as response:
                try:
                    logger.info(f"正在通过代理 {proxy} 访问 {url}")
                    json_data = await response.json()
                    logger.info(f"代理响应: {response.status}")

                except aiohttp.ContentTypeError:
                    json_data = {}
                if not response.ok:
                    return {'error': True, 'status': response.status, 'data': json_data}
                return json_data
    except Exception as e:
        logger.error(f"Error in coday: {e}")
        return {'error': True, 'message': str(e)}

# 读取令牌、唯一 ID 和代理
async def read_tokens_ids_and_proxies():
    try:
        # 读取 token 文件
        async with aiofiles.open('token.txt', 'r') as f:
            token_data = await f.read()
        tokens = [line.strip() for line in token_data.split('\n') if line.strip()]

        # 读取唯一 ID 文件
        async with aiofiles.open('unique_id.txt', 'r') as f:
            ids_data = await f.read()
        unique_ids = [line.strip() for line in ids_data.split('\n') if line.strip()]

        # 询问用户是否使用代理
        use_proxy = True

        proxies = []
        if use_proxy:
            # 读取代理文件
            async with aiofiles.open('proxy.txt', 'r') as f:
                proxy_data = await f.read()
            proxies = [line.strip() for line in proxy_data.split('\n') if line.strip()]

            # 检查 token、唯一 ID 和代理的行数是否匹配
            if len(tokens) != len(unique_ids) or len(tokens) != len(proxies):
                logger.error("Token、唯一 ID 和代理的行数不匹配。")
                return []

        # 组合账户信息
        accounts = []
        for i in range(len(tokens)):
            access_token, refresh_token = map(str.strip, tokens[i].split('|'))
            ids = list(map(str.strip, unique_ids[i].split('|')))
            proxy = proxies[i] if use_proxy else None
            proxy_type = 'socks5' if proxy and proxy.startswith('socks5://') else 'http'
            accounts.append({'access_token': access_token, 'refresh_token': refresh_token, 'unique_ids': ids, 'proxy': f"{proxy_type}://{proxy}" if proxy else None})
        # logger.info(f"accounts:{accounts}")
        return accounts
    except Exception as e:
        logger.error(f"读取 token、唯一 ID 或代理文件失败: {e}")
        return []
# 刷新令牌功能
async def refresh_token(refresh_token, account_index, proxy):
    logger.info(f"正在刷新账户 {account_index + 1} 的访问令牌...{proxy}")
    payload_data = {'refresh_token': refresh_token}
    response = await coday("https://api.meshchain.ai/meshmain/auth/refresh-token", 'POST', headers, payload_data, proxy=proxy)

    if response and response.get('access_token'):
        # 更新 token 文件
        async with aiofiles.open('token.txt', 'r') as f:
            token_lines = (await f.read()).split('\n')
        token_lines[account_index] = f"{response['access_token']}|{response['refresh_token']}"
        async with aiofiles.open('token.txt', 'w') as f:
            await f.write('\n'.join(token_lines))
        logger.info(f"账户 {account_index + 1} 的令牌刷新成功")
        return response['access_token']
    logger.error(f"账户 {account_index + 1} 的令牌刷新失败")
    return None

# info 函数
async def info(unique_id, headers, proxy):
    url = 'https://api.meshchain.ai/meshmain/nodes/status'
    return await coday(url, 'POST', headers, {'unique_id': unique_id}, proxy=proxy)

# estimate 函数
async def estimate(unique_id, headers, proxy):
    url = 'https://api.meshchain.ai/meshmain/rewards/estimate'
    return await coday(url, 'POST', headers, {'unique_id': unique_id}, proxy=proxy)

# claim 函数
async def claim(unique_id, headers, proxy):
    # 判断下tokens 够不够
    url = 'https://api.meshchain.ai/meshmain/rewards/claim'
    result = await coday(url, 'POST', headers, {'unique_id': unique_id}, proxy=proxy)
    return result.get('total_reward', None)

# start 函数
async def start(unique_id, headers, proxy):
    url = 'https://api.meshchain.ai/meshmain/rewards/start'
    return await coday(url, 'POST', headers, {'unique_id': unique_id}, proxy=proxy)

# tokens 函数
async def tokens(unique_id, headers, proxy):
    url = 'https://api.meshchain.ai/meshmain/wallet/tokens'
    result = await coday(url, 'GET', headers, {'unique_id': unique_id}, proxy=proxy)
    return result.get('data', [])


# 单个账户的主要处理流程
async def process_account(account, account_index):
    global headers
    headers['Authorization'] = f"Bearer {account['access_token']}"

    for unique_id in account['unique_ids']:
        proxy = account['proxy']

        # 获取用户信息
        profile = await info(unique_id, headers, proxy)
        logger.info(f"info profile result: {profile}")
        if profile.get('error'):
            logger.error(f"账户 {account_index + 1} | {unique_id}: 获取用户信息失败，尝试刷新令牌...")
            new_access_token = await refresh_token(account['refresh_token'], account_index, proxy)
            if not new_access_token:
                return
            headers['Authorization'] = f"Bearer {new_access_token}"
        else:
            
            cycle_started_at = profile.get('cycle_started_at')
            cycle_ended_at = profile.get('cycle_ended_at')
            last_claimed_at = profile.get('last_claimed_at')

            if not cycle_started_at:
                await start(unique_id, headers, proxy)
                continue
            

                
                # 获取当前 UTC 时间
            current_time = datetime.datetime.now(datetime.timezone.utc)
            logger.info(f"当前服务器时间: {current_time.isoformat()}")
            if last_claimed_at:
                last_claimed_at = datetime.datetime.fromisoformat(last_claimed_at.replace("Z", "+00:00"))
                logger.info(f"{account_index + 1} | {unique_id} 最近领取时间: {last_claimed_at.isoformat()}")

            # 将 cycle_ended_at 转换为 datetime 对象
            cycle_end_time = datetime.datetime.fromisoformat(cycle_ended_at.replace("Z", "+00:00"))
            logger.info(f"{account_index + 1} | {unique_id} 任务结束时间: {cycle_end_time.isoformat()}")

            # 比较时间
            if current_time <= cycle_end_time:
                logger.info(f"{account_index + 1} | {unique_id} 当前时间小于 cycle_ended_at，未到领取时间，不进行提前领取操作。")
                await asyncio.sleep(2)  # 每 60 秒运行一次
                continue
            elif  last_claimed_at and  last_claimed_at>=cycle_end_time:
                logger.info(f"{account_index + 1} | {unique_id} 最新领取时间大于 cycle_ended_at，领过了，不进行重复领取操作。")
                await asyncio.sleep(2)  # 每 60 秒运行一次
                continue
            else:
                time_diff = current_time - cycle_end_time
                logger.info(f"{account_index + 1} | {unique_id}  当前时间大于等于 cycle_ended_at，开始执行领取操作...")
            name = profile.get('name')
            is_linked = profile.get('is_linked')

            total_reward = profile.get('total_reward')
            logger.info(f"账户 {account_index + 1} | {unique_id}: {name} | 余额: {total_reward} 连接状态:{is_linked}")

        # 获取奖励估算
        filled = await estimate(unique_id, headers, proxy)
        logger.info(f"estimate result:{filled}")
        estimate_value=filled.get('value', 0)
        if not filled:
            logger.error(f"账户 {account_index + 1} | {unique_id}: 获取估算值失败。")
            continue
        else:
            logger.error(f"账户 {account_index + 1} | {unique_id}: 获取估算{estimate_value}")

        if filled.get('value', 0) >= 25.2:
            logger.info(f"账户 {account_index + 1} | {unique_id}: 尝试领取奖励...")
            
            # 获取 claim_fee
            claim_fee = filled["claim_fee"]
            
            # 提取 amount 和 decimals
            amount_no_dec = claim_fee["amount_no_dec"]
            
            tokens_arr = await tokens(unique_id, headers, proxy)
            balance=0
            # 筛选出BNB的余额并去除18个零
            for token in tokens_arr:
                if token["symbol"] == "BNB":
                    balance_str = token["balance"]
                    balance = float(balance_str) / (10 ** 18)
            if balance < float(amount_no_dec):
                logger.error(f"账户 {account_index + 1} | {unique_id}: BNB 资金不够 balance {balance}< GAS需要{amount_no_dec}")
                continue
            reward = await claim(unique_id, headers, proxy)
            if reward:
                logger.info(f"账户 {account_index + 1} | {unique_id}: 奖励领取成功！新余额: {reward}")
                # await start(unique_id, headers, proxy)
                logger.info(f"账户 {account_index + 1} | {unique_id}: 重新新一轮 ，开始挖矿。")
            else:
                logger.error(f"账户 {account_index + 1} | {unique_id}: 领取奖励失败。")
                # await start(unique_id, headers, proxy)

        else:
            logger.info(f"账户 {account_index + 1} | {unique_id}: 已经在挖矿中，当前值: {filled.get('value', 0)}")

# 主流程处理所有账户
async def main():
    banner = "Your Banner Here"
    logger.debug(banner)

    while True:
        accounts = await read_tokens_ids_and_proxies()

        if not accounts:
            logger.error("没有账户可处理。")
            return

        for i, account in enumerate(accounts):
            logger.info(f"正在处理账户 {i + 1}...")
            await process_account(account, i)

        await asyncio.sleep(2*60)  # 每 60 秒运行一次

# 运行主流程
if __name__ == "__main__":
    asyncio.run(main())
