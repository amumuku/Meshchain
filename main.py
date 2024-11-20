import aiohttp
import asyncio
import aiofiles
import logging
import time

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
                    json_data = await response.json()
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
        use_proxy = input("是否使用代理？(y/n): ").strip().lower() == 'y'

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

        return accounts
    except Exception as e:
        logger.error(f"读取 token、唯一 ID 或代理文件失败: {e}")
        return []
# 刷新令牌功能
async def refresh_token(refresh_token, account_index, proxy):
    logger.info(f"正在刷新账户 {account_index + 1} 的访问令牌...")
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
    url = 'https://api.meshchain.ai/meshmain/rewards/claim'
    result = await coday(url, 'POST', headers, {'unique_id': unique_id}, proxy=proxy)
    return result.get('total_reward', None)

# start 函数
async def start(unique_id, headers, proxy):
    url = 'https://api.meshchain.ai/meshmain/rewards/start'
    return await coday(url, 'POST', headers, {'unique_id': unique_id}, proxy=proxy)

# 单个账户的主要处理流程
async def process_account(account, account_index):
    global headers
    headers['Authorization'] = f"Bearer {account['access_token']}"

    for unique_id in account['unique_ids']:
        proxy = account['proxy']

        # 获取用户信息
        profile = await info(unique_id, headers, proxy)

        if profile.get('error'):
            logger.error(f"账户 {account_index + 1} | {unique_id}: 获取用户信息失败，尝试刷新令牌...")
            new_access_token = await refresh_token(account['refresh_token'], account_index, proxy)
            if not new_access_token:
                return
            headers['Authorization'] = f"Bearer {new_access_token}"
        else:
            name = profile.get('name')
            total_reward = profile.get('total_reward')
            logger.info(f"账户 {account_index + 1} | {unique_id}: {name} | 余额: {total_reward}")

        # 获取奖励估算
        filled = await estimate(unique_id, headers, proxy)
        if not filled:
            logger.error(f"账户 {account_index + 1} | {unique_id}: 获取估算值失败。")
            continue

        if filled.get('value', 0) > 10:
            logger.info(f"账户 {account_index + 1} | {unique_id}: 尝试领取奖励...")
            reward = await claim(unique_id, headers, proxy)
            if reward:
                logger.info(f"账户 {account_index + 1} | {unique_id}: 奖励领取成功！新余额: {reward}")
                await start(unique_id, headers, proxy)
                logger.info(f"账户 {account_index + 1} | {unique_id}: 重新开始挖矿。")
            else:
                logger.error(f"账户 {account_index + 1} | {unique_id}: 领取奖励失败。")
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

        await asyncio.sleep(60)  # 每 60 秒运行一次

# 运行主流程
if __name__ == "__main__":
    asyncio.run(main())
