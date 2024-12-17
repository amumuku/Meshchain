# MESHCHAIN 网络

**MeshChain** 是一个去中心化网络，旨在为 AI 工作负载提供经济且可扩展的计算能力。它解决了 AI 资源的高成本和有限访问问题，使每个人都能够轻松地贡献并受益于 AI 的力量。

- [点击注册](https://app.meshchain.ai?ref=UXFQ1RX2KTZA)



---

## MeshChain 脚本

可以完成以下任务：
-多账户注册。
-可选是否使用代理。
-使用 OTP 验证邮箱。
-领取 BNB 奖励。
-初始化并链接独特节点。


---

## 环境要求

1. **Python 版本：**
   - 需要 Python 3.11 版本。

2. **依赖安装：**
   - 使用 `pip install -r requirements.txt` 安装所需依赖。

3. **邮箱要求：**
   - 每个账户需要一个新的邮箱（用于邮箱验证和领取奖励）。

4. **账户与节点限制：**
   - 每个账户只能链接一个节点。如果需要大量挖矿，请创建多个账户。

---

## 文件说明

1. **自动生成文件：**
   - 使用脚本注册账户后，系统会自动生成以下文件：
     - **`token.txt`**：存储账户的令牌，每行一个账户，格式为 `access_token|refresh_token`。
     - **`unique_id.txt`**：存储每个账户对应的节点唯一 ID，每行一个账户。

2. **手动创建文件（如果账户已存在）：**
   - 如果你已有账户，可以手动创建文件：
     - **`token.txt` 示例：**
       ```
       abc123def456|xyz789ghi012
     
       ```
     - **`unique_id.txt` 示例：**
       ```
       unique_id_1
  
       ```

---

## 使用方法

### 1. 克隆仓库
将代码克隆到本地：
```bash
git clone https://github.com/amumuku/Meshchain.git
cd Meshchain
```
### 2安装依赖
运行以下命令安装项目所需的依赖
```
pip install -r requirements.txt
```
### 3注册账户
运行以下命令启动注册脚本，按提示完成账户注册：
```
python register.py
```
输入用户名、邮箱、密码和邀请码，脚本会自动保存令牌到 token.txt，并将唯一 ID 保存到 unique_id.txt。
### 4启动脚本 注意 如果选择代理跑不起来 可以选择不使用代理
运行以下命令启动主脚本，完成奖励领取和挖矿任务
```
python main.py
```

