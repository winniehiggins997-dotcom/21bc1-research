# 21bc1-research
个人开发
# 21 Bitcoin Computer 开发与修改记录 (Changelog)

**最后更新时间**：2026-06-16 18:35 (当地时间)

本记录详细说明了对项目脚本进行的所有修复和完善，确保与本地 `two1` 库接口的正确适配。

---

## ✅ 第一轮修改（2026-06-16 11:25）

### 1.1 修复 `example_wallet.py`
- **修改原因**：
  - 原脚本中调用了钱包对象不存在的方法 `wallet.current_receive_address()`。
  - 原脚本中尝试读取不存在的属性 `wallet.master_public_key`。
- **修改方案**：
  - 将 `wallet.current_receive_address()` 变更为 `@property` 属性 `wallet.current_address`（去除了小括号 `()` ）。
  - 将 `wallet.master_public_key` 修改为从底层 HD 密钥派生主公钥的正确 API 形式：`wallet.w._master_key.public_key.to_b58check(wallet.w.testnet)`。
- **修改作用**：
  - 恢复了本地 HD 钱包接口的基本可用性，避免了未定义方法/属性的 `UndefinedMethodError` 报错。

### 1.2 修复 `payment_api_demo.py`
- **修改原因**：
  - 动态计价接口 `/api/length-calculator` 和它的计价回调函数 `get_dynamic_price()` 使用了 `request` 对象，但在 Flask 模块导入部分中并未导入 `request`，导致运行时抛出 `NameError: name 'request' is not defined`。
- **修改方案**：
  - 在 `create_payment_app()` 内的 Flask 导入语句中添加了对 `request` 的导入：
    ```python
    from flask import Flask, jsonify, request
    ```
- **修改作用**：
  - 修复了运行时因缺失 `request` 导致的 API 闪退问题，确保微支付网关能正常获取客户端请求参数并动态计价。

---

## 2. 21 Bitcoin Computer 硬件引脚与接线说明 (供更换开发板参考)

如果您打算使用其他开发板（如 **ESP32** 等）来控制 21 Bitcoin Computer 的矿机扩展板（HAT），请参考以下硬件接口定义：

### 2.1 主通信接口：SPI 候选接口
矿片（ASIC，板上疑似标记区域为 `U15`）与主机之间的主通信协议尚未实测确认。Raspberry Pi 40-Pin 排针上具备标准 SPI0 引脚，因此 SPI 是一个需要抓包验证的候选接口，引脚定义如下：

| 信号名称 (Signal) | 树莓派物理引脚 (Physical Pin) | GPIO (BCM) | 作用 (Function) | ESP32 推荐接线建议 |
| :--- | :--- | :--- | :--- | :--- |
| **SPI_MOSI** | Pin 19 | GPIO 10 | 数据输出 | 连接至 ESP32 VSPI_MOSI (GPIO 23) 或 HSPI_MOSI (GPIO 13) |
| **SPI_MISO** | Pin 21 | GPIO 9 | 数据输入 | 连接至 ESP32 VSPI_MISO (GPIO 19) 或 HSPI_MISO (GPIO 12) |
| **SPI_SCLK** | Pin 23 | GPIO 11 | 时钟信号 | 连接至 ESP32 VSPI_CLK (GPIO 18) 或 HSPI_CLK (GPIO 14) |
| **SPI_CE0** (CS) | Pin 24 | GPIO 8 | 片选信号 | 连接至 ESP32 指定的片选 GPIO (如 GPIO 5 或 GPIO 15) |

> [!NOTE]
> **协议疑问（重要）**：经过查阅资料发现，21 Bitcoin Computer 内部实际使用的通信协议**可能是 UART 而非 SPI**。同时代的 Bitmain BM1385 等 SHA-256 ASIC 芯片普遍使用 UART 串口链通信（CI/CO/RI/RO 四线制）。21 Inc 的协议细节属于专有信息，未公开文档。**建议**：在实际接线前，使用逻辑分析仪抓取树莓派与矿板之间的实际通信信号，确认协议类型和波特率/时钟速率。

### 2.2 控制与状态拓展：I2C 接口与 MCP23008
该 HAT 板载了一片 **MCP23008** 8位 I/O 拓展芯片（在板上标记为 `U12`），用于提供额外的控制线（如矿片的 Reset 复位控制信号、工作指示 LED、中断控制等）。
主机通过 I2C 接口与 MCP23008 交互：
- **SDA** (Data): 物理 Pin 3 (GPIO 2)
- **SCL** (Clock): 物理 Pin 5 (GPIO 3)

**MCP23008 引脚功能说明**：

| MCP23008 引脚 | 功能 | 说明 |
| :--- | :--- | :--- |
| Pin 1-2 (SCL/SDA) | I2C 总线 | 与主机通信 |
| Pin 3-5 (A2/A1/A0) | I2C 地址配置 | 若全部接 GND，I2C 地址为 **0x20** |
| Pin 6 (/RESET) | 芯片复位（低有效） | 必须上拉至 VDD 才能正常工作；若接 GND 则芯片持续复位 |
| Pin 8 (INT) | 中断输出 | 可不接；若需要中断检测再连 |
| Pin 9 (VSS) | 地 | 接 GND |
| Pin 10-17 (GP0-GP7) | 通用 I/O | 连接至 ASIC 的 Reset/Enable/状态指示等控制线；注意 MCP23008 的 GP7 为输出专用脚 |
| Pin 18 (VDD) | 电源 | 接 3.3V |

> [!IMPORTANT]
> **调试建议**：在树莓派上运行 `i2cdetect -y 1`，若 MCP23008 正常工作且地址引脚全接 GND，应在地址 `0x20` 处看到响应。若通信异常，请检查 SDA/SCL 线上是否有 4.7kΩ 上拉电阻。

### 2.3 电平转换说明
- **重要提示**：板上配备了 **AVCH16T245** 类双电源总线收发/电平转换芯片（板上标记为 `U1`），用于在树莓派 3.3V 逻辑侧与矿片 ASIC 逻辑侧之间做电平转换。
- **准确性校正**：该类器件不是“自动方向识别”的双向转换器，而是需要通过 `DIR` 控制传输方向、通过 `OE` 控制输出使能。实际开发时必须确认 `DIR/OE` 由谁控制，以及 A/B 两侧分别接哪个电压域。
- **接线注意**：ESP32 的 I/O 端口运行电平同样为 **3.3V**，因此可以直接与扩展板的 40-Pin 插座接口连线，无需额外的电平转换模块。请确保共地（GND 相连），并通过外部 DC Jack 为扩展板提供充足的矿机电源输入。

### 2.4 minerd 软件架构与通信说明（补充，已校正）

根据 `two1/commands/mine.py` 源码分析：
- **启动命令**：`sudo minerd -u <用户名> <矿池URL>`
  - `two1` 源码默认矿池 URL 为：`swirl+tcp://grid.21.co:21006`（定义于 `two1/__init__.py` 的 `TWO1_POOL_URL`）。
  - `two1/commands/mine.py` 中实际启动命令形式为：`sudo minerd -u config.username two1.TWO1_POOL_URL`。
- **状态通信**：minerd 进程启动后，通过 Unix Domain Socket（`/tmp/minerd.sock`）向外发布 JSON 格式事件。
- **PID 文件**：`/run/minerd.pid`，用于检测 minerd 是否已在运行。
- **协议注意**：原 `two1` 软件使用 `swirl+tcp://` URL，不能直接等同于现代矿池常见的 `stratum+tcp://`。如果后续自研 ESP32/新主控要连接现代矿池，应单独实现标准 Stratum client，并把 Stratum job 转换为 ASIC 可接受的 work。

### 2.5 ESP32 替换方案参考：Bitaxe 开源项目

如果您准备用 ESP32 替换树莓派来驱动矿片，强烈建议参考 **Bitaxe** 开源项目，这是目前最成熟的 ESP32 驱动比特币 ASIC 矿机方案：

| 项目 | 链接 | 说明 |
| :--- | :--- | :--- |
| **ESP-Miner 固件** | [github.com/bitaxeorg/ESP-Miner](https://github.com/bitaxeorg/ESP-Miner) | ESP32-S3 驱动 BM1366 ASIC 的完整开源固件（含 Stratum 协议、WiFi、Web GUI） |
| **Bitaxe Ultra 硬件** | [github.com/bitaxeorg/bitaxe](https://github.com/bitaxeorg/bitaxe) | KiCad 原理图和 PCB 文件 |
| **OSMU 社区** | [osmu.wiki](https://osmu.wiki) | 开源矿机开发社区 Wiki，包含 BM1366 通信协议逆向工程文档 |

**Bitaxe 方案关键技术细节**（可类比参考）：
- ESP32-S3 通过 **UART** 与 BM1366 ASIC 通信（BM1366 逻辑电平 **1.8V**，需电平转换）。
- I2C 控制 DS4432 数字电位器调节核心电压，优化算力/功耗比。
- ESP32 运行 **AxeOS** 固件，通过 WiFi 连接 Stratum 矿池。
- 21 Bitcoin Computer 的矿片通信协议与此类似，但具体寄存器地址和命令格式为专有，需用逻辑分析仪逆向。

> [!WARNING]
> **注意**：21 Bitcoin Computer 的矿片和 BM1366 是不同的 ASIC 芯片，其通信协议并不相同。Bitaxe 的代码可以作为 ESP32+ASIC 系统架构的参考，但不能直接复用。您需要在树莓派原系统运行时用逻辑分析仪抓包，确定 21 矿片的实际通信协议后，再编写对应的 ESP32 驱动代码。

---

## ✅ 第二轮修改（2026-06-16 11:49）

### 2.1 深度修复 `example_wallet.py` — `demo_crypto_fallback()` 函数

- **修改原因**：
  - `HDPrivateKey.from_random()` 在 `two1` 库中根本不存在，会抛出 `AttributeError`。
  - 子密钥不应通过 `.child_key(44, is_prime=True)` 链式调用派生（该 API 不适用于 HD 路径），应使用 `HDKey.from_path(master_key, "44'/0'/0'/0/0")` 并取最后一个元素。
  - `HDPrivateKey` 没有 `.to_wif()` 方法（WIF 是普通私钥的格式，HD 私钥使用 Base58Check 序列化），会抛出 `AttributeError`。
- **修改方案**：
  - 将 `HDPrivateKey.from_random()` 改为 `HDPrivateKey.master_key_from_entropy(passphrase='')` 并接收返回的元组 `(master_key, mnemonic)`，同时打印助记词供备份。
  - 将链式 `.child_key()` 调用改为 `HDKey.from_path(master_key, "44'/0'/0'/0/0")[-1]`，使用官方支持的路径派生方式。
  - 将 `.to_wif()` 改为 `.to_b58check()`，正确序列化 HD 私钥。
- **修改作用**：
  - `demo_crypto_fallback()` 函数现在可以正确生成随机 HD 钱包并派生 BIP44 子地址，不再崩溃。

### 2.2 深度修复 `payment_api_demo.py` — 变量名遮蔽 (Name Shadowing)

- **修改原因**：
  - 在 `create_payment_app()` 内定义的动态定价回调函数 `get_dynamic_price(request, ...)` 中，参数名 `request` 与外层通过 `from flask import request` 导入的模块变量同名，造成变量名遮蔽。虽然在该回调函数内部不产生立即错误，但会导致代码可读性差，且若内外层调用混用会引发逻辑错误。
- **修改方案**：
  - 将 `get_dynamic_price` 回调函数的参数 `request` 重命名为 `req`，同时将函数体内对 `request.args` 的引用改为 `req.args`。
- **修改作用**：
  - 消除变量名遮蔽问题，代码更清晰，避免潜在的作用域混乱 Bug。

### 2.3 修复 `monitor_minerd.py`

- **修改 1：移除未使用的 `timestamp` 变量**
  - **原因**：`parse_event()` 函数第 65 行读取了 `timestamp = event.get("timestamp", "")` 但该变量从未被使用，属于无用代码（dead code），注释掉并说明其用途备查。
  - **作用**：代码更整洁，消除潜在的 linting 警告。

- **修改 2：添加 Windows 平台兼容性警告**
  - **原因**：`socket.AF_UNIX`（Unix Domain Socket）在 Windows 上不可用，若在 Windows 上直接运行会在 `socket.socket(socket.AF_UNIX, ...)` 行抛出 `AttributeError`，不如提前检测并给出友好提示。
  - **方案**：在脚本顶部（导入之后）添加 `sys.platform == 'win32'` 检测，若是 Windows 则打印警告并调用 `sys.exit(1)` 退出。
  - **作用**：提升脚本的健壮性和可用性，在 Windows 环境下给出明确的平台不支持提示，而不是一个晦涩的系统错误。

---

## ✅ 第三轮检查与修复（2026-06-16 11:58）

### 本轮工作：通过查阅真实源码进行 API 正确性二次验证

**验证方法**：通过 AST 解析 `two1_source/two1-3.10.9/two1/bitcoin/crypto.py`，列举所有类方法名，并提取具体方法源码，进行逐一比对。

### 验证结论

| 方法/接口 | 存在性 | 签名 | 使用方式 |
|---|---|---|---|
| `HDPrivateKey.master_key_from_entropy(passphrase='')` | ✅ 存在 | 返回 `(HDPrivateKey, str)` 元组 | ✅ 正确 |
| `HDKey.from_path(root_key, path_str)` | ✅ 存在 | 返回 `list[HDKey]` | ✅ 正确，用 `[-1]` 取末尾子密钥 |
| `HDKey.to_b58check(testnet=False)` | ✅ 存在 | 返回 `str` | ✅ 正确 |
| `public_key.address()` | ✅ 存在 | 返回 `str` | ✅ 正确 |
| `payment.required(price)` | ✅ 存在于 `decorator.py:76` | `price` 可为 `int` 或 `callable` | ✅ 正确 |
| 动态计价回调调用方式 | ✅ `decorator.py:89` 确认 | `price(request, *args, **kwargs)` | ✅ 我们的 `get_dynamic_price(req,...)` 正确 |

**路径解析验证**：通过运行 Python 脚本确认路径 `"44'/0'/0'/0/0"` 被 `parse_path()` 正确分割为 BIP44 标准段，硬化导出索引计算正确（`44 | 0x80000000 = 0x8000002C`）。

### 本轮新增修复

#### 修复 `example_wallet.py` — 无用导入注释缺失

- **原因**：`test_imports()` 中导入了 `Transaction` 和 `HDPublicKey`，但这两个名称在函数体内并未直接使用，容易被 linting 工具（如 Flake8）标记为 `F401 imported but unused`，让人误以为是遗留错误代码。
- **方案**：为这两行导入添加 `# noqa: F401` 注释，并加上中文说明，解释它们的导入目的是"做模块可用性验证测试"，而非实际使用。
- **作用**：代码意图清晰，消除误解，同时保留了完整的模块加载可用性测试能力。

### 整体状态总结

经过三轮检查与修复，三个脚本目前存在的**所有可识别错误均已修复**：

| 文件 | 状态 |
|---|---|
| `monitor_minerd.py` | ✅ 逻辑正确，平台兼容性警告已添加 |
| `example_wallet.py` | ✅ 所有 API 调用均已核实与源码一致 |
| `payment_api_demo.py` | ✅ Flask 路由、装饰器用法、变量名均已正确 |

---

## ✅ 第四轮：实际运行测试与修复（2026-06-16 12:09）

### 本轮工作：安装依赖 → 实际运行 → 发现真实报错 → 修复 → 清理环境

### 4.1 安装环境说明

**临时安装的包**（测试完毕后已全部卸载）：
`two1`, `arrow`, `base58`, `mnemonic`, `protobuf`, `flask`, `blinker`, `itsdangerous`, `werkzeug`, `pyaes`, `tabulate`, `path`, `path.py`, `pexpect`, `ptyprocess`, `pbkdf2`

**安装方式**：`pip install --no-deps -e two1_source/two1-3.10.9`（绕过不兼容的 protobuf==3.0.0a3）

---

### 4.2 修复 `two1/bitcoin/block.py` — sha256 C 扩展无法编译

- **修改时间**：2026-06-16 12:04
- **修改原因**：
  - `block.py` 第 4 行 `from sha256 import sha256 as sha256_midstate` 是顶层导入。
  - `sha256` 是 21 Bitcoin Computer 专用 C 扩展，需要 MSVC 编译器，在普通 Windows 开发机上无法编译。
  - 此导入导致整个 `two1` 库（包括钱包、加密模块）都无法导入，属于"连带崩溃"。
- **修改方案**：
  - 将顶层导入改为懒加载（在 `_compute_midstate()` 函数内按需导入）。
  - 添加 `try/except ImportError` 回退：若 C 扩展不可用，回退到 `hashlib` 实现的兼容版本。
- **修改文件**：`two1_source/two1-3.10.9/two1/bitcoin/block.py`
- **修改作用**：
  - `two1` 库现在可以在没有编译环境的 Windows PC 上正常导入。
  - 挖矿功能在树莓派（有 C 扩展）上继续使用原始高性能实现，不受影响。

---

### 4.3 修复 `two1/channels/database.py` — fcntl 在 Windows 不可用

- **修改时间**：2026-06-16 12:06
- **修改原因**：
  - `database.py` 第 3 行 `import fcntl`，该模块是 Linux/macOS 专用文件锁，Windows 无此模块。
  - 导入链：`two1.bitserv.flask → payment_server → channels → database` → 触发 `ModuleNotFoundError: No module named 'fcntl'`。
  - `payment_api_demo.py` 因此无法运行。
- **修改方案**：
  - 检测 `sys.platform == 'win32'`，在 Windows 下定义 `_FcntlShim` 类，用 `msvcrt.locking` 模拟 `fcntl.lockf` 的加锁/解锁操作。
  - 在 Unix/Linux 下保持原始 `import fcntl` 不变。
- **修改文件**：`two1_source/two1-3.10.9/two1/channels/database.py`
- **修改作用**：
  - `two1.bitserv.flask.Payment` 现在可以在 Windows 上正常导入，不再因 `fcntl` 崩溃。

---

### 4.4 修复 `example_wallet.py` — bytes 输出未解码

- **修改时间**：2026-06-16 12:07
- **修改原因**：
  - `to_b58check()` 和 `address()` 返回 `bytes` 类型，直接用 `format()` 打印会显示 `b'...'` 前缀，影响可读性。
- **修改方案**：
  - 对两个返回值判断 `isinstance(..., bytes)` 后执行 `.decode('utf-8')`。
- **修改作用**：
  - 输出内容为纯文本字符串，如 `xprvA3...`、`1CmC2...`，无 `b'...'` 前缀。

---

### 4.5 修复 `payment_api_demo.py` — Wallet() 无配置文件时崩溃

- **修改时间**：2026-06-16 12:07
- **修改原因**：
  - `create_payment_app()` 里直接 `wallet = Wallet()` 无任何保护，在没有 `~/.two1/wallet/default_wallet.json` 的机器上直接抛出 `FileNotFoundError` 并崩溃。
  - `__main__` 块没有检查 `create_payment_app()` 可能返回 `None`，直接调用 `app.run()` 会引发 `AttributeError: 'NoneType'`。
- **修改方案**：
  - 将 `Wallet()` 包在 `try/except` 里，失败时打印友好提示并 `return None`。
  - 在 `__main__` 里检查 `if app is None`，若为空则打印中止信息，否则正常启动 Flask。
- **修改作用**：
  - 在没有钱包的 PC 上运行时，给出清晰的操作指引，不再崩溃。

---

### 4.6 最终实际运行结果

**`example_wallet.py`** ✅ 完整输出正常：
```
[1/3] -> [成功] two1 库核心模块导入成功！
[2/3] -> [提示] 钱包初始化失败（无配置文件，属正常）
[3/3] -> [成功] 已成功在内存中生成随机主私钥！
      -> 助记词 (Mnemonic): erosion coffee pass goddess ...
      -> 派生子私钥 (Base58Check): xprvA3ATU18SWJFkEK...
      -> 派生子地址: 1CmC2yoiTa4EiuTBBnYo6PxtBsvEf8tRCi
```

**`payment_api_demo.py`** ✅ 完整输出正常：
```
[1/3] -> [成功] Flask 已安装
      -> [成功] two1 核心微支付模块成功导入
[提示] 本地钱包初始化失败（无配置文件，属正常）
[中止] 因钱包初始化失败，无法启动 Flask 服务。
       请先在 21 Bitcoin Computer 上初始化钱包后再运行本脚本。
```

**`monitor_minerd.py`** ✅ 平台检测正常（在 Windows 上正确退出并提示）

### 4.7 清理说明

测试完毕后，已通过以下命令卸载全部临时依赖：
```
pip uninstall -y two1 arrow base58 mnemonic protobuf flask blinker itsdangerous werkzeug pyaes tabulate path path.py pexpect ptyprocess pbkdf2
```
环境已恢复原始状态。

---

## ✅ 第五轮：全局导入排查与深层 Windows 兼容性修复 (2026-06-16 12:25)

### 5.1 本轮工作：编写自动化脚本，全量测试 `two1` 的所有子模块导入

为了确保没有隐蔽的 Windows 平台导入崩溃错误，我们编写了脚本逐个对 `two1` 子模块进行 `importlib.import_module`，成功发掘了多处由于运行环境更新、缺少依赖以及平台假设不一致导致的致命崩溃，并逐一进行了深度修复。

---

### 5.2 修复 `two1/sell/installer.py` —— Windows 下导入直接抛出 `FileNotFoundError`

- **修改原因**：
  - `InstallerMac` 类中，直接在类属性级别（类加载时即执行）声明了：
    ```python
    VERSION_OS = subprocess.check_output(["uname", "-s"]).decode()
    VERSION_HW = subprocess.check_output(["uname", "-m"]).decode()
    ```
  - 这导致在 Windows 下即便不实例化该类，在 `import two1.sell.installer` 时就会因为系统找不到 `uname` 编译工具而抛出 `FileNotFoundError: [WinError 2]`，进而阻断了整个 `two1.sell` 库的导入。
- **修改方案**：
  - 将此两处命令的执行加上了平台检查限制：
    ```python
    VERSION_OS = subprocess.check_output(["uname", "-s"]).decode() if sys.platform != 'win32' else ''
    VERSION_HW = subprocess.check_output(["uname", "-m"]).decode() if sys.platform != 'win32' else ''
    ```
- **修改作用**：
  - 彻底解决了 Windows 平台下导入 `installer.py` 的崩溃问题，使相关销售管理脚本对跨平台有更好的容错性。

---

### 5.3 修复 `two1/commands/util/version.py` —— pkg_resources 升级导致 `SetuptoolsVersion` 导入崩溃

- **修改原因**：
  - 新版 `pkg_resources`（Setuptools）由于架构重构，已经移除了旧的内部类 `SetuptoolsVersion`。
  - 直接导入 `from pkg_resources import SetuptoolsVersion` 会引发 `ImportError: cannot import name 'SetuptoolsVersion'`。
- **修改方案**：
  - 移除了对该类的直接导入，并利用 `try-except` 重构了版本号比对函数 `is_version_gte`。
  - 优先调用标准 `parse_version` 比较，并在解析抛出异常（例如对于特殊字尾 `-v7+` 等）时，优雅地回退至 `LooseVersion` 或字符串比较。
- **修改作用**：
  - 修复了因为 `setuptools` 升级导致的全局版本控制工具导入崩溃。

---

### 5.4 修复 `two1/sell/composer.py` —— 缺少 `docker-py` 导致导入崩溃

- **修改原因**：
  - 脚本在头部直接 `from docker import Client`。如果用户的 Python 环境没有安装 docker SDK 驱动，在导入该模块时会抛出 `ModuleNotFoundError`。
- **修改方案**：
  - 对 docker 的模块导入实施了惰性/安全包装（`try-except` 捕获）：
    ```python
    try:
        from docker import Client
        from docker.utils import kwargs_from_env as docker_env
    except ImportError:
        Client = None
        docker_env = None
    ```
  - 同时在两个 `connect` 连接方法内添加了防空断言。如果用户未安装 `docker-py` 并调用该方法，将抛出清晰的 `ImportError` 引导其进行安装，而非爆出其他非预期异常。
- **修改作用**：
  - 确保即使在未装 Docker 的机器上，其余核心微支付功能亦可正常导入不受干扰。

---

### 5.5 发掘缺失依赖 `pbkdf2` & `protobuf`

- **发掘原因**：
  - 经查 `two1/wallet/two1_wallet.py` 调用了 `from pbkdf2 import PBKDF2`；并且 `two1/server/swirl_pb3.py` 调用了 `protobuf`，但在 `install_requires` 中并未完整锁死，甚至 `pbkdf2` 在依赖链中被遗漏。
- **修复方案**：
  - 测试期间我们手动将 `pbkdf2` 和 `protobuf` 补充安装至运行环境，并在 `test_imports.py` 中预先指定 `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` 确保 protobuf 协议描述符兼容性。
  - 已在本次文档中详细记载。若用户后续在 Linux 主机上全功能布署，需注意用 `pip install pbkdf2 protobuf` 补充以上被 two1 遗留的包。

---

### 5.6 最终验证与环境清理

- **验证**：
  - 经测试，所有 `two1` 子模块目前除了平台强相关的 OpenSSL 硬件加密调用（已在 `ecdsa.py` 内部有 Python Fallback 捕获）以及 Django 框架集成（已提供友好的 Django 依赖检查异常）外，其余均在 Windows 上可以顺利无错导入！
  - 再次启动 `example_wallet.py` 和 `payment_api_demo.py`，输出验证完全符合预期，业务功能闭环。
- **再次清理**：
  - 所有为排查而增装的额外测试库（含 `protobuf` 和 `pbkdf2` 等）现已再次完整卸载：
    ```
    pip uninstall -y two1 arrow base58 mnemonic protobuf flask blinker itsdangerous werkzeug pyaes tabulate path path.py pexpect ptyprocess pbkdf2
    ```
  - 本地 Python 开发环境依然保持 100% 洁净状态。

---

## ✅ 第六轮：微支付模块配置鲁棒性优化 (2026-06-16 12:28)

### 6.1 优化 `two1/bitserv/payment_methods.py` 中的 `BitTransfer` 初始化

- **优化原因**：
  - 在 `Payment` 微支付装饰器初始化时，默认会自动激活并初始化 `BitTransfer` 支付方式。
  - 原本的 `BitTransfer` 构造函数在 `username` 参数为空时，直接尝试打开全局配置文件 `~/.two1/two1.json` 并读取 `username` 属性，没有加任何异常保护。
  - 这导致在未配置全局账户环境的普通机器上（即便存在本地钱包，但不存在 `two1.json` 配置文件，或配置文件中无 `username` 键名），运行任何微支付 Flask 路由保护时，一初始化 `Payment(app, wallet)` 就会抛出 `FileNotFoundError` 或 `KeyError` 阻断启动，哪怕应用根本不需要也没人能用起已失效的 `BitTransfer` 协议。
- **优化方案**：
  - 对 `BitTransfer` 类的全局配置读取加了 `try-except (FileNotFoundError, KeyError, ValueError)` 保护：
    ```python
    try:
        with open(acct, 'r') as f:
            account = json.loads(f.read())
        self.seller_username = account['username']
    except (FileNotFoundError, KeyError, ValueError):
        self.seller_username = None
    ```
  - 并在 `redeem_payment` 进行实际交易验证的入口处补充了健全性拦截：若配置无商户 `seller_username`，抛出对应的 `PaymentError` 说明情况。
  - 在返回 `402` 响应头时对空用户名值做回退处理：`self.seller_username or ""`。
- **优化作用**：
  - 彻底规避了在干净环境下初始化 `Payment` 对象时因 `two1.json` 缺失造成的连带崩溃，大幅提高了离线开发与测试的稳定度和容忍度。

---

## ✅ 第七轮：资料索引与项目全貌补充 (2026-06-16 12:40)

### 7.1 当前资料目录总览

本目录当前保存的是一套围绕 **21 Bitcoin Computer / two1 Python 库 / 本地微支付 API / 挖矿监控 / 硬件接线分析** 的综合资料。整体可分为以下几类：

| 路径 | 类型 | 说明 |
|---|---|---|
| `development_log.md` | 开发记录 | 本项目的主说明文档，记录所有修复、验证、硬件分析与后续建议 |
| `example_wallet.py` | 示例脚本 | 本地 HD 钱包与离线密钥生成示例，可在不依赖 21.co 云服务的情况下测试底层钱包能力 |
| `payment_api_demo.py` | 示例脚本 | Flask + `two1.bitserv` 微支付 API 示例，包含免费接口、固定价格付费接口、动态计价接口 |
| `monitor_minerd.py` | 监控脚本 | 监听 `/tmp/minerd.sock`，解析 minerd 矿工进程输出的 JSON 状态事件 |
| `two1_source/two1-3.10.9/` | 源码目录 | `two1` 3.10.9 完整源码，已做若干 Windows 兼容性与鲁棒性修复 |
| `two1_download/two1-3.10.9.tar.gz` | 原始包 | 原始下载的 `two1` 源码压缩包，便于回溯或重新解压对比 |
| `图片/` | 硬件照片 | 21 Bitcoin Computer 硬件、HAT 扩展板、风扇、散热器、ASIC 芯片与接口细节照片 |

### 7.2 顶层脚本用途说明

#### `example_wallet.py`

该脚本用于验证 `two1` 钱包与加密模块是否可用，适合在普通 PC 上做离线开发测试。

- 检查 `two1.wallet`、`two1.bitcoin.txn`、`two1.bitcoin.crypto` 是否能正常导入。
- 尝试读取本地 21 钱包配置，并输出当前接收地址、余额、主公钥。
- 若本地没有 21 钱包配置，则使用 `HDPrivateKey.master_key_from_entropy()` 在内存中生成临时 HD 钱包。
- 使用 BIP44 路径 `"44'/0'/0'/0/0"` 派生子私钥和比特币地址。

适合用途：
- 验证 `two1` 库是否修复到可导入、可调用状态。
- 在没有 21.co 云端服务的情况下测试本地钱包和 HD 密钥逻辑。
- 为后续编写离线交易、签名或地址生成工具提供参考。

#### `payment_api_demo.py`

该脚本用于演示 21 体系中“付费 API”的基本工作方式。

- 使用 Flask 创建本地 HTTP API 服务。
- 使用 `two1.bitserv.flask.Payment` 为路由添加 HTTP 402 Payment Required 保护。
- `/api/free`：免费接口，不需要支付。
- `/api/premium`：固定价格接口，示例价格为 1000 satoshis。
- `/api/length-calculator`：动态计价接口，根据 `word` 参数长度按字符计费。

注意事项：
- 实际启动微支付服务需要本地存在有效的 21 钱包配置。
- 在普通 PC 上没有钱包时，脚本会友好退出，不再直接崩溃。
- 该脚本更适合在 21 Bitcoin Computer 或已迁移钱包配置的 Linux 环境中测试完整闭环。

#### `monitor_minerd.py`

该脚本用于监控 21 Bitcoin Computer 上的 `minerd` 挖矿进程状态。

- 监听 Unix Domain Socket：`/tmp/minerd.sock`。
- 解析 `StatisticsEvent`，输出运行时间、温度、5/15/60 分钟平均算力。
- 解析 `ShareSubmitEvent`，输出 share 提交结果、Work ID、Nonce。
- 其他事件会以 JSON 格式直接打印。

注意事项：
- 该脚本依赖 `socket.AF_UNIX`，仅适用于 Linux/macOS。
- Windows 上运行会直接提示平台不支持并退出。
- 运行前需确保 `minerd` 已启动，并且 `/tmp/minerd.sock` 存在。

### 7.3 `two1` 源码目录结构说明

`two1_source/two1-3.10.9/two1/` 下主要模块如下：

| 模块 | 作用 |
|---|---|
| `wallet/` | HD 钱包、交易构造、UTXO 选择、余额查询、钱包缓存 |
| `bitcoin/` | 比特币基础结构，包括区块、交易、脚本、哈希、密钥与地址 |
| `crypto/` | ECDSA、OpenSSL、Python fallback 等加密实现 |
| `bitserv/` | 服务端微支付能力，包含 Flask/Django 集成与支付方法 |
| `bitrequests/` | 客户端付费请求封装 |
| `channels/` | 支付通道实现，包含状态机、数据库、客户端与服务端逻辑 |
| `blockchain/` | 区块链数据提供者接口，包括 Insight、Mock、TwentyOne provider |
| `commands/` | `two1` 命令行工具的各个子命令，如 `mine`、`wallet`、`sell`、`buy` |
| `sell/` | API 出售、服务管理、Docker/ZeroTier/Composer 相关逻辑 |
| `server/` | 21 服务端通信、认证、消息封装与 protobuf 文件 |
| `mkt/` | 市场相关接口 |
| `lib/` | 辅助库入口 |

### 7.4 已确认的关键修复点

当前源码和脚本中已完成的关键适配包括：

- 修复 `example_wallet.py` 中不存在的 `wallet.current_receive_address()` 和 `wallet.master_public_key` 调用。
- 修复 HD 钱包生成逻辑，改用真实存在的 `HDPrivateKey.master_key_from_entropy()` 与 `HDKey.from_path()`。
- 修复 `payment_api_demo.py` 中 Flask `request` 未导入和变量名遮蔽问题。
- 为 `payment_api_demo.py` 添加钱包缺失时的友好退出逻辑。
- 为 `monitor_minerd.py` 添加 Windows 平台不支持提示。
- 将 `two1/bitcoin/block.py` 中的 `sha256` C 扩展改为懒加载，并增加 `hashlib` fallback。
- 为 `two1/channels/database.py` 增加 Windows 下的 `fcntl` 兼容处理。
- 修复 `two1/sell/installer.py` 在 Windows 下导入时调用 `uname` 导致的崩溃。
- 修复 `two1/commands/util/version.py` 对新版 setuptools 中已移除 `SetuptoolsVersion` 的依赖。
- 修复 `two1/sell/composer.py` 在缺少 `docker-py` 时导入即崩溃的问题。
- 优化 `two1/bitserv/payment_methods.py` 中 `BitTransfer` 对 `~/.two1/two1.json` 缺失的容错能力。

### 7.5 硬件照片内容说明

`图片/` 目录下共有 6 张照片，内容均与 21 Bitcoin Computer 硬件有关：

| 文件名 | 内容概述 |
|---|---|
| `image_editor_1781509814177.jpg` | 21 Bitcoin Computer 整体外观，带外壳与 HAT 板边缘 |
| `image_editor_1781509820096.jpg` | HAT 扩展板正面全景，可见 40-pin 接口、DC 电源座、板号与芯片布局 |
| `image_editor_1781509825746.jpg` | 板侧视角，可见散热器内部结构、固定柱与排针 |
| `image_editor_1781509830306.jpg` | 风扇与散热结构近照 |
| `image_editor_1781509835478.jpg` | PCB 局部细节，可见 MCP23008、AVCH16T245、接口与测试点区域 |
| `image_editor_1781509839332.jpg` | ASIC 芯片近照，可见裸芯/封装标记区域，适合辅助识别矿片型号 |

### 7.6 硬件分析要点补充

结合照片与现有文档，目前可确认或需进一步验证的硬件要点如下：

- HAT 板上存在 `MCP23008` I/O 扩展芯片，推测通过 I2C 与主机通信，地址可能为 `0x20`。
- HAT 板上存在 `AVCH16T245` 电平转换芯片，用于主机 3.3V 逻辑与矿片侧逻辑之间的电平转换。
- 40-pin 排针可用于从树莓派引出 SPI/I2C/GPIO 等信号，但矿片主通信协议仍需实测确认。
- 虽然资料中列出了 SPI 连接推测，但 21 Bitcoin Computer 的 ASIC 通信也可能更接近 UART 链式协议。
- 若计划用 ESP32 替换树莓派，不能直接假设 SPI 或直接套用 Bitaxe 固件，必须先抓取原机通信波形。

### 7.7 后续建议

如果继续推进本项目，建议按以下顺序进行：

1. 在原 21 Bitcoin Computer 或树莓派环境中启动 `minerd`，确认 `/tmp/minerd.sock` 的真实事件格式。
2. 使用逻辑分析仪同时抓取 40-pin 接口上的 SPI、UART、I2C 相关信号，确认矿片实际通信协议。
3. 记录启动阶段、复位阶段、挖矿任务下发阶段、share 返回阶段的波形与数据包。
4. 将抓包结果整理为协议文档，再决定 ESP32 端驱动是走 SPI、UART 还是其他 GPIO 时序。
5. 若目标是复活软件生态，优先完善 `example_wallet.py` 与 `payment_api_demo.py` 的可运行环境说明。
6. 若目标是替换控制板，优先建立“树莓派原机行为复刻”测试，而不是直接移植 Bitaxe。

---

## ✅ 第八轮：面向零件开发的工程资料补充 (2026-06-16 13:05)

### 8.1 开发目标定义

本节面向“开发这个零件”的实际工程推进，默认目标是围绕 **21 Bitcoin Computer 矿机 HAT/ASIC 控制板** 做二次开发、替代控制板或兼容驱动开发。

可选开发目标分为三档：

| 目标档位 | 目标说明 | 难度 | 推荐程度 |
|---|---|---|---|
| A. 原机资料复原 | 记录引脚、电源、I2C、minerd 事件和系统运行方式 | 低 | 必做 |
| B. 外部主控接管 | 使用 ESP32/STM32/RP2040 等开发板替代树莓派控制 HAT | 中高 | 推荐分阶段做 |
| C. 自研兼容矿机板 | 重新设计 PCB、电源、风扇、主控、ASIC 通信与矿池协议 | 高 | 需完成协议逆向后再做 |

当前最现实的路线是：

1. 先让原 21 Bitcoin Computer 正常启动并挖矿或至少运行 `minerd`。
2. 抓取树莓派与 HAT 之间的真实信号。
3. 用开发板复刻原机初始化流程。
4. 最后再设计自己的硬件。

### 8.2 零件/板卡初步功能分解

从照片和现有资料推测，这块 HAT/矿机板至少包含以下功能单元：

| 功能单元 | 可能器件/区域 | 作用 | 开发关注点 |
|---|---|---|---|
| 主机接口 | 40-pin 排母 | 与树莓派连接，传输 GPIO/I2C/SPI/UART/电源相关信号 | 必须确认真实信号，不可只按树莓派默认 SPI 推断 |
| ASIC 矿片 | 照片中的大芯片/裸芯区域 | 执行 SHA-256 计算 | 需要确认型号、供电、电平、初始化命令 |
| I/O 扩展 | `MCP23008` | 提供复位、使能、LED、状态等控制线 | 可通过 I2C 扫描和寄存器读写验证 |
| 电平转换 | `AVCH16T245` | 主机 3.3V 与矿片侧逻辑电平转换 | 需确认 A/B 两侧电压、方向控制、OE 引脚 |
| 电源输入 | DC Jack 与电源区域 | 给 ASIC、风扇、逻辑芯片供电 | 需测量输入电压、电流、各路稳压输出 |
| 散热系统 | 风扇、散热器、导热结构 | 保证 ASIC 温度稳定 | 需确认风扇电压、控制方式、温度保护策略 |
| 状态/测试点 | TPxx 测试点 | 调试、生产测试或内部信号引出 | 需建立测试点表格 |

### 8.3 必须先采集的基础数据

在开发前，建议建立一份 `hardware_notes.md` 或继续在本文档中追加以下实测数据。没有这些数据就直接接 ESP32，容易误判协议甚至损坏硬件。

| 数据项 | 采集方法 | 记录格式 |
|---|---|---|
| DC 输入电压 | 万用表测 DC Jack 输入 | 例如：`Vin = 12.0V` |
| 待机电流 | 电源表串联测量 | 例如：`idle = 0.18A` |
| 挖矿电流 | 原机运行 `minerd` 时测量 | 例如：`mining = 1.2A` |
| 3.3V 轨 | 万用表测逻辑供电 | 标注测点和电压 |
| ASIC 核心电压 | 测电感/稳压输出附近 | 标注测点和电压，注意短路风险 |
| I2C 地址 | 树莓派运行 `i2cdetect -y 1` | 记录所有响应地址 |
| 40-pin 信号活动 | 逻辑分析仪抓取 | 保存 `.sal` 或 CSV |
| minerd socket 事件 | 运行 `monitor_minerd.py` | 保存原始 JSON |
| 启动日志 | `dmesg`、系统服务日志、minerd 输出 | 保存完整文本 |

### 8.4 40-pin 接口开发检查表

先按树莓派 40-pin 标准接口建立排查表。下表不是最终结论，而是开发时的测量模板。

| 物理引脚 | 常见功能 | 开发板连接建议 | 必测内容 |
|---|---|---|---|
| Pin 1 | 3.3V | 只作参考电压，不建议外部反灌 | 是否稳定为 3.3V |
| Pin 2/4 | 5V | 谨慎连接，确认是否由树莓派供电或被 HAT 反供 | 是否存在 5V |
| Pin 3 | GPIO2/SDA | ESP32 I2C SDA 可参考接入 | 是否有 I2C 波形 |
| Pin 5 | GPIO3/SCL | ESP32 I2C SCL 可参考接入 | 是否有 I2C 时钟 |
| Pin 6/9/14/20/25/30/34/39 | GND | 必须共地 | 地线连续性 |
| Pin 19 | GPIO10/MOSI | SPI 假设信号 | 是否有高速数据输出 |
| Pin 21 | GPIO9/MISO | SPI 假设信号 | 是否有返回数据 |
| Pin 23 | GPIO11/SCLK | SPI 假设信号 | 是否存在时钟 |
| Pin 24 | GPIO8/CE0 | SPI 片选假设 | 是否随数据拉低 |
| Pin 8/10 | UART TX/RX | UART 假设信号 | 是否存在串口波形、波特率 |
| 其他 GPIO | 复位/中断/LED/电源使能候选 | 暂不直接驱动 | 先抓启动时序 |

重要原则：

- ESP32 与 HAT 必须共地。
- 不确认方向的信号先只用逻辑分析仪高阻探测，不要主动输出。
- 不确认电压的信号先用万用表/示波器测电平，不要直接接 5V 不耐受引脚。
- 任何电源轨都不要反向供电，尤其是 HAT 已接 DC Jack 时。

### 8.5 逻辑分析仪抓包方案

建议使用 8 通道以上逻辑分析仪，采样率优先设置为 20 MHz 或更高。如果怀疑 SPI 时钟较高，应提高到 50 MHz 或 100 MHz。

第一阶段抓取通道：

| 通道 | 建议连接 | 目的 |
|---|---|---|
| CH0 | GND 参考 | 所有测量共地 |
| CH1 | SDA / Pin 3 | 捕获 I2C 配置 |
| CH2 | SCL / Pin 5 | 捕获 I2C 配置 |
| CH3 | MOSI / Pin 19 | 捕获 SPI 数据输出 |
| CH4 | MISO / Pin 21 | 捕获 SPI 数据输入 |
| CH5 | SCLK / Pin 23 | 捕获 SPI 时钟 |
| CH6 | CE0 / Pin 24 | 捕获 SPI 片选 |
| CH7 | UART TX 或疑似 ASIC 数据线 | 验证是否为 UART |

抓包场景必须分开保存：

1. 上电但不启动挖矿。
2. 启动 `minerd` 的前 10 秒。
3. 成功连接矿池后收到第一批 work。
4. 提交 share 时刻。
5. 停止 `minerd` 或系统关机时刻。

建议文件命名：

```text
capture_01_power_on_idle.sal
capture_02_minerd_start.sal
capture_03_first_work.sal
capture_04_share_submit.sal
capture_05_shutdown.sal
```

### 8.6 判断 SPI 还是 UART 的方法

不要只根据引脚名称判断协议，应以波形为准。

SPI 特征：

- 有明显连续时钟 SCLK。
- CE/CS 在一帧数据期间拉低。
- MOSI/MISO 与 SCLK 同步变化。
- 数据速率通常较高，空闲时 SCLK 不跳变。

UART 特征：

- 没有独立时钟线。
- 单根 TX/RX 数据线出现异步脉冲。
- 可用常见波特率解码，如 115200、230400、500000、1000000、3000000。
- 数据帧通常为 8N1，空闲电平为高。

I2C 特征：

- SDA/SCL 两线均为开漏上拉。
- 有地址帧、ACK 位。
- MCP23008 若地址为 `0x20`，会在 I2C 解码中明显出现。

如果启动阶段同时出现 I2C 配置和 UART/SPI 数据，通常说明：

- I2C 用于复位、使能、LED 或辅助控制。
- UART/SPI 用于 ASIC 主数据通信。

### 8.7 ESP32 替代控制板的最小原型方案

推荐先做“外接飞线原型”，不要一开始画 PCB。

最小硬件：

| 模块 | 推荐选择 | 说明 |
|---|---|---|
| 主控 | ESP32-S3 DevKit | GPIO 充足，USB 调试方便，性能比普通 ESP32 更好 |
| 逻辑电平 | 默认 3.3V | 先接 HAT 的 40-pin 主机侧，不直接接 ASIC 侧 |
| 电源 | HAT 使用原 DC Jack，ESP32 使用 USB | 两边必须共地，避免从 ESP32 给 HAT 主供电 |
| 调试 | USB 串口 + 逻辑分析仪 | 同时看固件日志和总线波形 |
| 安全保护 | 串联 100Ω-330Ω 电阻 | 对未知 GPIO 线做限流保护 |

最小固件功能：

1. 启动后扫描 I2C，确认 MCP23008 是否在线。
2. 读取 MCP23008 寄存器默认值。
3. 复刻树莓派启动时对 MCP23008 的配置写入。
4. 只做复位/使能控制，不发送 ASIC 任务。
5. 确认风扇、电源、状态 LED 行为正常。
6. 再开始复刻 UART/SPI 初始化包。

### 8.8 ESP32 固件模块建议

后续固件建议按模块拆分：

```text
firmware/
  main/
    app_main.c
    board_pins.h
    board_power.c
    board_power.h
    mcp23008.c
    mcp23008.h
    asic_transport.c
    asic_transport.h
    asic_protocol.c
    asic_protocol.h
    stratum_client.c
    stratum_client.h
    web_status.c
    web_status.h
```

模块职责：

| 模块 | 职责 |
|---|---|
| `board_pins.h` | 集中定义 ESP32 到 HAT 的引脚映射 |
| `mcp23008.*` | I2C 扩展芯片寄存器读写 |
| `board_power.*` | 复位、使能、风扇、电源状态管理 |
| `asic_transport.*` | SPI/UART 底层收发，不包含协议语义 |
| `asic_protocol.*` | ASIC 初始化、下发 work、读取 nonce |
| `stratum_client.*` | 连接矿池、订阅、授权、接收 job |
| `web_status.*` | Web 页面或 JSON API 输出算力、温度、错误状态 |

### 8.9 软件复刻路线

原 `two1` 体系的软件逻辑可作为参考，但不建议直接在 ESP32 上移植 Python 代码。

建议拆解为三层：

| 层级 | 原系统对应 | ESP32/自研系统对应 |
|---|---|---|
| 上层网络 | `minerd` 连接 Stratum 矿池 | ESP32 Stratum client |
| 中层任务 | `minerd` 生成/分发 work | 固件 job manager |
| 底层硬件 | 树莓派与 HAT/ASIC 通信 | `asic_transport` + `asic_protocol` |

开发顺序：

1. 先让 ESP32 能控制 MCP23008，完成 reset/enable。
2. 再让 ESP32 发送原机抓包中的初始化序列。
3. 再让 ESP32 发送固定测试 work。
4. 能读回 nonce 后，再接 Stratum。
5. 最后做 Web 状态页、矿池配置、温度/风扇控制。

### 8.10 PCB 自研前置条件

如果目标是重新画板，至少需要先完成以下条件：

- 已确认 ASIC 型号或至少确认通信协议。
- 已确认 ASIC 核心电压、I/O 电压、峰值电流。
- 已确认复位、时钟、使能、数据输入输出时序。
- 已确认散热方案能稳定压住温度。
- 已确认 Stratum 到 ASIC work 的转换过程。
- 已有飞线原型成功跑出 nonce 或有效 share。

未满足以上条件前，不建议直接画 PCB。否则最可能出现的问题是：板子能上电，但 ASIC 不响应，且无法判断是电源、时序、协议还是焊接问题。

### 8.11 初版自研板功能建议

若进入 PCB 阶段，初版板卡不追求小型化，优先追求可测、可修、可观察。

建议包含：

| 功能 | 建议 |
|---|---|
| 主控 | ESP32-S3-WROOM 模块 |
| USB | USB-C 下载与日志 |
| 电源 | DC 输入，独立 5V/3.3V/ASIC Core 稳压 |
| 测试点 | 所有关键电源、复位、UART/SPI、I2C、时钟都引出 |
| 风扇 | 2-pin 常开或 4-pin PWM，优先简单可靠 |
| 温度 | NTC 或数字温度传感器，靠近 ASIC |
| 状态灯 | Power、ASIC Ready、Mining、Error |
| 调试接口 | UART 下载口、JTAG 或备用 GPIO 排针 |
| 保护 | 输入保险丝/TVS/反接保护，关键 IO 串阻 |

### 8.12 风险清单

| 风险 | 表现 | 规避方式 |
|---|---|---|
| 协议判断错误 | 接线正确但 ASIC 无响应 | 先抓原机波形，不凭猜测写驱动 |
| 电平不匹配 | GPIO 发热、芯片损坏 | 先测电压，再接线，必要时加电平转换 |
| 电源能力不足 | 启动掉电、算力不稳定 | 用可调电源观察电流峰值 |
| 散热不足 | ASIC 很快过热或停止 | 先保留原散热器和风扇 |
| I2C 控制缺失 | ASIC 不上电或不退出复位 | 先复刻 MCP23008 寄存器写入 |
| Stratum 实现不完整 | 能连矿池但无有效 share | 先用固定 work 验证底层，再接矿池 |
| 原 21.co 服务失效 | 旧命令无法登录/发布 | 本地离线逻辑与标准矿池协议分开处理 |

### 8.13 当前最小任务清单

下一步可以直接执行的任务：

1. 给每张硬件照片标注芯片型号、接口、测试点编号。
2. 在原机上运行 `i2cdetect -y 1`，确认 MCP23008 地址。
3. 在原机上运行 `monitor_minerd.py`，保存真实 JSON 事件样本。
4. 用逻辑分析仪抓取启动与挖矿阶段的 I2C/SPI/UART 波形。
5. 根据抓包结果补充 `protocol_notes.md`。
6. 写一个 ESP32 I2C 扫描 + MCP23008 读写测试固件。
7. 用 ESP32 复刻 reset/enable 时序。
8. 再决定是否进入 ASIC 数据协议复刻。

### 8.14 建议新增资料文件

为了后续开发更清晰，建议后续新增以下文档：

| 文件名 | 内容 |
|---|---|
| `hardware_notes.md` | 实测电压、电流、芯片型号、测试点、接口定义 |
| `protocol_notes.md` | 逻辑分析仪抓包结果、SPI/UART/I2C 解码、初始化序列 |
| `esp32_plan.md` | ESP32 引脚映射、固件模块、开发进度 |
| `bom_draft.md` | 自研板候选 BOM、器件型号、电源规格 |
| `test_checklist.md` | 上电、通信、散热、挖矿、长稳测试清单 |

### 8.15 当前结论

这块零件的开发关键不在普通软件接口，而在 **确认 ASIC 的真实通信协议和电源/复位时序**。现有 `two1` 源码、示例脚本和硬件照片已经足够作为起点，但还缺少原机运行时的总线抓包。

因此，下一阶段的核心目标应是：

```text
先测量和抓包 -> 再复刻控制时序 -> 再写 ESP32/新主控驱动 -> 最后设计自研 PCB
```

---

## ✅ 第九轮：树莓派使用资料补充 (2026-06-16 13:25)

### 9.1 树莓派在本项目中的角色

在 21 Bitcoin Computer 原始架构中，树莓派不是普通显示/联网模块，而是整套矿机控制系统的主机。它承担以下职责：

| 职责 | 说明 |
|---|---|
| 系统主控 | 运行 Linux、`two1` CLI、`minerd` 等软件 |
| HAT 控制 | 通过 40-pin 排针控制矿机 HAT 的 I2C/GPIO/SPI/UART 信号 |
| 钱包与账户 | 保存本地钱包配置、签名支付请求、运行 21 微支付工具 |
| 挖矿任务 | 启动 `minerd`，在原 two1 环境中连接 `swirl+tcp://grid.21.co:21006`；自研新主控时可另行实现现代 Stratum |
| 状态输出 | 通过 `/tmp/minerd.sock` 输出 JSON 状态事件 |
| 网络连接 | 通过以太网/WiFi 连接矿池、API 服务或局域网调试机 |

因此，如果要开发这块零件，树莓派最重要的用途是 **作为原机参考控制器**：先让原始系统跑起来，再观察它如何初始化 HAT、如何控制 ASIC、如何输出状态。

### 9.2 推荐树莓派型号与系统

21 Bitcoin Computer 原机时代通常基于 Raspberry Pi 2/3 级别硬件。做开发时可按以下建议选择：

| 项目 | 推荐 |
|---|---|
| 树莓派型号 | Raspberry Pi 3B/3B+ 更方便；Raspberry Pi 2 也可作原机还原 |
| 系统 | Raspberry Pi OS Lite 32-bit 优先 |
| Python | 原 `two1` 更适合 Python 3.4/3.5/3.6 时代；现代系统需做兼容处理 |
| 网络 | 优先有线网，便于稳定连接矿池和 SSH |
| 供电 | 树莓派独立稳定 5V 电源；HAT 矿机部分使用原 DC Jack |
| 存储卡 | 16GB 以上，建议先完整备份镜像 |

注意：

- 如果手上有 21 Bitcoin Computer 原始 SD 卡，优先完整克隆，不要直接在原卡上实验。
- 原 21.co 账户、市场、登录等云服务大概率已经失效，开发重点应放在本地钱包、HAT 控制、原机 `minerd` 行为记录、现代 Stratum 适配和硬件逆向。
- 新版 Raspberry Pi OS 可能与旧 `two1` 依赖不兼容，建议用虚拟环境隔离测试。

### 9.3 首次上电安全检查

树莓派插上 HAT 前，先完成以下检查：

| 检查项 | 操作 | 目标 |
|---|---|---|
| 外观检查 | 看是否有烧毁、电容鼓包、松动排针、风扇卡死 | 避免短路或机械故障 |
| 电源极性 | 测 DC Jack 正负极 | 防止反接 |
| 3.3V/5V 短路 | 万用表电阻档测电源轨到 GND | 确认无明显短路 |
| 风扇 | 手动拨动风扇叶片 | 确认不卡滞 |
| 散热器 | 检查是否压紧 ASIC | 避免上电后快速过热 |
| 排针方向 | 确认 40-pin 插接方向 | 避免错位插入 |

上电顺序建议：

1. 不插 HAT，先启动树莓派，确认系统正常。
2. 关机断电。
3. 插入 HAT，先只接树莓派电源，不接 HAT DC Jack，测是否有异常发热。
4. 关机断电。
5. 接 HAT DC Jack 和树莓派电源，观察电流和风扇。
6. 若有可调电源，建议给 HAT 设置电流限制后再上电。

### 9.4 树莓派基础系统配置

建议先启用 SSH，方便远程操作：

```bash
sudo raspi-config
```

建议开启：

| 配置项 | 作用 |
|---|---|
| SSH | 远程登录调试 |
| I2C | 扫描 MCP23008 等 I2C 设备 |
| SPI | 验证 HAT 是否使用 SPI |
| Serial Port | 验证 UART 是否参与 ASIC 通信 |
| Expand Filesystem | 扩展 SD 卡空间 |

也可手动编辑。新版 Raspberry Pi OS 常用路径是 `/boot/firmware/config.txt`；旧系统可能是 `/boot/config.txt`：

```bash
sudo nano /boot/firmware/config.txt
```

确认或添加：

```text
dtparam=i2c_arm=on
dtparam=spi=on
enable_uart=1
```

重启：

```bash
sudo reboot
```

### 9.5 常用调试工具安装

建议在树莓派上安装以下工具：

```bash
sudo apt update
sudo apt install -y i2c-tools spi-tools minicom screen python3-pip python3-venv git htop lsof
```

工具用途：

| 工具 | 用途 |
|---|---|
| `i2cdetect` | 扫描 I2C 总线设备 |
| `i2cget` / `i2cset` | 读取/写入 I2C 寄存器 |
| `spidev_test` | 验证 SPI 设备通信 |
| `minicom` / `screen` | 查看 UART 串口数据 |
| `lsof` | 查看 `/tmp/minerd.sock`、设备文件占用 |
| `htop` | 查看进程和 CPU 状态 |
| `python3-venv` | 隔离 Python 依赖 |

### 9.6 I2C 检查 MCP23008

启用 I2C 后，先扫描总线：

```bash
i2cdetect -y 1
```

预期：

- 若 MCP23008 地址脚 A0/A1/A2 都接 GND，常见地址为 `0x20`。
- 如果看到 `20`，说明 I2C 总线至少能访问到该芯片。
- 如果没有任何设备，检查 SDA/SCL、上拉电阻、HAT 供电、I2C 是否启用。

读取 MCP23008 常用寄存器：

| 寄存器 | 地址 | 说明 |
|---|---|---|
| IODIR | `0x00` | IO 方向，1 输入，0 输出 |
| IPOL | `0x01` | 输入极性反转 |
| GPINTEN | `0x02` | 中断使能 |
| DEFVAL | `0x03` | 默认比较值 |
| INTCON | `0x04` | 中断控制 |
| IOCON | `0x05` | 配置寄存器 |
| GPPU | `0x06` | 上拉使能 |
| INTF | `0x07` | 中断标志 |
| INTCAP | `0x08` | 中断捕获 |
| GPIO | `0x09` | 当前 GPIO 值 |
| OLAT | `0x0A` | 输出锁存 |

示例读取：

```bash
i2cget -y 1 0x20 0x00
i2cget -y 1 0x20 0x09
i2cget -y 1 0x20 0x0A
```

警告：

- 不要在未确认 GP0-GP7 连接含义前随意 `i2cset` 写输出值。
- 某些位可能控制 ASIC reset、enable 或电源，错误写入可能导致异常上电或停机。
- 先记录原机启动前、启动后、运行 `minerd` 后的寄存器变化，再复刻。

### 9.7 SPI 检查

确认 SPI 设备存在：

```bash
ls /dev/spidev*
```

常见结果：

```text
/dev/spidev0.0
/dev/spidev0.1
```

查看内核模块：

```bash
lsmod | grep spi
```

如果怀疑 HAT 使用 SPI 与 ASIC 通信，不建议一开始主动发送数据。应先用逻辑分析仪抓取树莓派运行原始软件时的 SPI 波形。

可观察的关键线：

| 树莓派物理引脚 | BCM | SPI 功能 |
|---|---|---|
| Pin 19 | GPIO10 | MOSI |
| Pin 21 | GPIO9 | MISO |
| Pin 23 | GPIO11 | SCLK |
| Pin 24 | GPIO8 | CE0 |
| Pin 26 | GPIO7 | CE1 |

判断依据：

- 启动 `minerd` 时若 SCLK 与 CE0 明显活动，说明 SPI 参与主通信的可能性高。
- 如果 I2C 有配置动作，但 SPI 无持续活动，应重点检查 UART 或其他 GPIO。

### 9.8 UART 检查

启用 UART 后，确认设备：

```bash
ls -l /dev/serial0 /dev/ttyAMA0 /dev/ttyS0
```

如果要观察串口，可用：

```bash
screen /dev/serial0 115200
```

但在未确认 HAT 是否接入树莓派默认 UART 前，不要随意向串口发送数据。优先使用逻辑分析仪被动抓取 Pin 8/10 或疑似 UART 测试点。

常见波特率候选：

```text
115200
230400
500000
1000000
1500000
3000000
```

如果抓到的波形没有 SPI 时钟但能被 UART 解码，下一步应记录：

- 波特率
- 数据位/停止位/校验
- 启动阶段初始化包
- work 下发包
- nonce 返回包

### 9.9 two1 源码在树莓派上的使用建议

当前项目中已经有 `two1_source/two1-3.10.9/`，建议在树莓派上优先用本地源码安装，而不是直接 `pip install two1`。

推荐流程：

```bash
cd ~/21-lnc
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -e two1_source/two1-3.10.9
```

如果遇到旧依赖不兼容，可参考本项目已有修复记录，并补装：

```bash
pip install flask arrow base58 mnemonic pyaes tabulate path.py pexpect pbkdf2 protobuf
```

注意：

- 某些旧版本 protobuf 依赖可能与现代 Python 冲突。
- 如果 `swirl_pb3.py` 报 descriptor 兼容问题，可临时设置：

```bash
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
```

建议把该变量写入当前 shell 或启动脚本中，而不是全局污染系统环境。

### 9.10 运行示例脚本

复制本项目到树莓派后，可先运行离线钱包脚本：

```bash
python example_wallet.py
```

预期：

- 如果 `two1` 模块导入成功，会显示核心模块导入成功。
- 如果没有本地钱包配置，钱包初始化会提示失败，但底层 HD 临时钱包生成仍应可用。
- 如果在原 21 系统上已有钱包配置，则可能显示当前接收地址和余额。

运行微支付 API 示例：

```bash
python payment_api_demo.py
```

预期：

- 有钱包配置时，服务启动在 `http://0.0.0.0:5000`。
- 局域网其他设备可访问 `http://<树莓派IP>:5000/api/free`。
- 付费接口需要有效 payment header，否则会返回 HTTP 402。

### 9.11 minerd 使用与监控

原资料中提到的启动方式：

```bash
sudo minerd -u <用户名> <矿池URL>
```

`two1` 原生示例：

```bash
sudo minerd -u username swirl+tcp://grid.21.co:21006
```

如果后续自研固件连接现代矿池，才使用常见的 `stratum+tcp://...` URL，并需要自己实现 Stratum 协议到 ASIC work 的转换。

运行后检查进程：

```bash
ps aux | grep minerd
```

检查 PID 文件：

```bash
ls -l /run/minerd.pid
```

检查 socket：

```bash
ls -l /tmp/minerd.sock
```

运行本项目监控脚本：

```bash
python monitor_minerd.py
```

如果成功连接，应能看到：

- `StatisticsEvent`
- 当前运行时间
- 平均算力
- 温度
- share 提交事件

建议保存原始事件：

```bash
python monitor_minerd.py | tee minerd_events.log
```

### 9.12 树莓派配合逻辑分析仪抓包

树莓派是抓包阶段的参考主机。建议让树莓派正常运行原始控制程序，同时用逻辑分析仪被动监听 40-pin 信号。

推荐流程：

1. 树莓派关机。
2. 连接逻辑分析仪 GND 到 HAT/树莓派 GND。
3. 连接 CH1-CH7 到 I2C/SPI/UART 候选引脚。
4. 先启动逻辑分析仪采集。
5. 给树莓派和 HAT 上电。
6. 通过 SSH 启动 `minerd`。
7. 保存启动、初始化、挖矿、停止阶段的波形。

建议同步记录树莓派终端输出：

```bash
dmesg -w
```

另一个 SSH 窗口记录：

```bash
python monitor_minerd.py | tee minerd_events.log
```

这样可把波形时间点与 `minerd` 事件对应起来。

### 9.13 常见故障排查

| 问题 | 可能原因 | 排查方式 |
|---|---|---|
| `i2cdetect` 看不到 `0x20` | I2C 未启用、HAT 未供电、SDA/SCL 接触不良 | 检查 `raspi-config`、测 3.3V、重插 HAT |
| `/dev/spidev*` 不存在 | SPI 未启用 | 开启 `dtparam=spi=on` 后重启 |
| `/tmp/minerd.sock` 不存在 | `minerd` 未启动或启动失败 | 查 `ps aux`、`journalctl`、手动启动 |
| `monitor_minerd.py` 无法连接 | socket 权限或 minerd 未运行 | 用 `ls -l /tmp/minerd.sock` 查看权限 |
| HAT 发热但无算力 | ASIC 未初始化、协议不通、矿池连接失败 | 看 `minerd` 日志和总线波形 |
| 风扇不转 | 风扇供电未启用、风扇损坏、HAT 电源未接 | 测风扇两端电压 |
| 树莓派重启或掉线 | 电源不足或 HAT 反灌/干扰 | 使用独立电源，检查 5V 电压跌落 |
| two1 导入失败 | Python/依赖版本不兼容 | 使用虚拟环境和本项目修复版源码 |

### 9.14 建议保存的树莓派资料

后续建议从树莓派导出以下资料，补充到项目目录：

| 文件名 | 内容 |
|---|---|
| `raspi_i2cdetect.txt` | `i2cdetect -y 1` 输出 |
| `raspi_gpio_readall.txt` | GPIO 状态输出，若安装了相关工具 |
| `raspi_dmesg_boot.txt` | 启动日志 |
| `minerd_events.log` | `monitor_minerd.py` 捕获的事件 |
| `minerd_process.txt` | `ps aux | grep minerd` 输出 |
| `spidev_devices.txt` | `/dev/spidev*` 与 SPI 模块状态 |
| `serial_devices.txt` | `/dev/serial0`、`ttyAMA0`、`ttyS0` 状态 |
| `power_measurements.md` | 上电、待机、挖矿时电压电流记录 |

### 9.15 树莓派阶段结论

树莓派阶段的目标不是马上替代原系统，而是把原系统的行为完整记录下来。只有当以下资料齐全后，才适合进入 ESP32 或自研控制板开发：

- I2C 地址和 MCP23008 寄存器变化记录。
- SPI/UART/GPIO 启动和挖矿阶段波形。
- `/tmp/minerd.sock` 原始事件样本。
- 电源输入、逻辑电压、ASIC 核心电压和电流记录。
- 原机从上电到开始挖矿的完整时序。

树莓派阶段的核心口号：

```text
先让原机说话，再让新主控模仿。
```

---

## ✅ 第十轮：外部资料核验、准确性审计与开源准备 (2026-06-16 14:05)

### 10.1 本轮核验目标

本轮目标是把本文档从“个人开发记录”提升为更适合开源的工程资料：

- 对关键硬件和软件结论补充来源。
- 把“已确认事实”“源码确认”“照片推测”“必须实测”区分开。
- 修正文档中不够准确的表述，尤其是 `minerd` 矿池协议和电平转换器方向控制。
- 为后续开源仓库提供引用资料清单和免责声明。

### 10.2 已核验资料来源

| 资料 | 来源 | 用途 |
|---|---|---|
| Raspberry Pi 40-pin GPIO、SPI/I2C/UART、3.3V GPIO 说明 | Raspberry Pi 官方文档：`https://www.raspberrypi.com/documentation/computers/raspberry-pi.html` | 校验 40-pin 引脚、SPI0、I2C、UART、GPIO 电压安全提示 |
| Raspberry Pi `config.txt`、`dtparam`、UART 配置 | Raspberry Pi 官方文档：`https://www.raspberrypi.com/documentation/computers/configuration.html` | 校验 `dtparam=i2c_arm=on`、`dtparam=spi=on`、`enable_uart` 等配置 |
| MCP23008 数据手册 | Microchip 数据手册：`https://ww1.microchip.com/downloads/aemDocuments/documents/APID/ProductDocuments/DataSheets/MCP23008-and-MCP23008-Data-Sheet-DS20001919.pdf` | 校验 I2C 地址、寄存器表、引脚功能、GP7 限制 |
| SN74AVCH16T245 数据手册 | TI 数据手册：`https://www.ti.com/lit/ds/symlink/sn74avch16t245.pdf` | 校验 `DIR/OE` 方向控制、电平转换范围、高阻状态要求 |
| two1 本地源码 | `two1_source/two1-3.10.9/` | 校验 `minerd` 启动命令、socket、PID 文件、HAT 识别方式、默认 pool URL |
| Bitaxe / ESP-Miner | `https://github.com/bitaxeorg/ESP-Miner`、`https://github.com/bitaxeorg/bitaxe` | 仅作为 ESP32 + ASIC 矿机架构参考，不作为 21 ASIC 协议依据 |

### 10.3 准确性审计结论

| 内容 | 当前状态 | 结论 |
|---|---|---|
| Raspberry Pi 40-pin 物理引脚 | 已由官方文档确认 | Pin 3/5 为 I2C SDA/SCL，Pin 19/21/23/24 为 SPI0 MOSI/MISO/SCLK/CE0，Pin 8/10 为 UART TX/RX |
| 树莓派 GPIO 电平 | 已由官方文档确认 | 普通 GPIO 为 3.3V 逻辑，不可接 5V 逻辑输入 |
| MCP23008 是 I2C I/O 扩展器 | 已由 Microchip 数据手册确认 | MCP23008 具备 8-bit I/O、I2C 接口、A2/A1/A0 三个地址脚 |
| MCP23008 地址 `0x20` | 条件确认 | 若 A2/A1/A0 全接 GND，则 7-bit I2C 地址为 `0x20`；实际板上地址仍需 `i2cdetect -y 1` 验证 |
| MCP23008 寄存器地址 | 已由数据手册确认 | `IODIR=0x00`、`IPOL=0x01`、`GPINTEN=0x02`、`DEFVAL=0x03`、`INTCON=0x04`、`IOCON=0x05`、`GPPU=0x06`、`INTF=0x07`、`INTCAP=0x08`、`GPIO=0x09`、`OLAT=0x0A` |
| MCP23008 GP7 能力 | 已校正 | 数据手册注明 MCP23008 的 GP7 为 output only；文档中已补充提醒 |
| AVCH16T245 类电平转换器 | 已由 TI 同类器件数据手册校正 | 它是双电源总线收发器，需要 `DIR` 和 `OE` 控制，不应描述为自动方向识别 |
| `minerd` socket | 已由本地源码确认 | `two1/commands/util/bitcoin_computer.py` 定义 `MINERD_SOCK = '/tmp/minerd.sock'` |
| `minerd` PID 文件 | 已由本地源码确认 | `two1/commands/mine.py` 使用 `/run/minerd.pid` |
| `minerd` 启动命令 | 已由本地源码确认 | 源码使用 `sudo minerd -u config.username two1.TWO1_POOL_URL` |
| two1 默认矿池 URL | 已由本地源码确认并校正 | `two1/__init__.py` 定义 `TWO1_POOL_URL = 'swirl+tcp://grid.21.co:21006'` |
| 21 ASIC 主通信协议 | 未确认 | SPI、UART 都只能作为候选，必须用逻辑分析仪抓包确认 |
| ASIC 型号 | 未确认 | 照片只能提供视觉线索，不能替代丝印/封装/电路追踪/原理图确认 |
| HAT 上每个测试点含义 | 未确认 | 需要逐点测量并建立测试点表 |

### 10.4 已修正的不准确或易误导表述

| 原表述 | 问题 | 当前修正 |
|---|---|---|
| “主通信接口：SPI 接口” | 暗示 ASIC 一定使用 SPI，但目前没有实测证据 | 改为“SPI 候选接口”，强调需抓包确认 |
| “`stratum+tcp://pool.21.co:3333`” | 与本地 `two1` 源码不一致 | 改为 `swirl+tcp://grid.21.co:21006`，并说明现代 Stratum 需另行实现 |
| “使用标准 Stratum 协议” | `two1` 原始软件使用 `swirl+tcp://`，不能直接等同于现代 Stratum | 改为“原 two1 使用 swirl；自研新主控再实现标准 Stratum” |
| “AVCH16T245 双向电平转换芯片” | 容易被理解为自动方向双向转换 | 改为“需要 `DIR/OE` 控制的双电源总线收发/电平转换芯片” |
| “MCP23008 GP0-GP7 都是通用 I/O” | MCP23008 的 GP7 有输出专用限制 | 增加 GP7 输出专用说明 |
| “编辑 `/boot/config.txt`” | 新版 Raspberry Pi OS 常用 `/boot/firmware/config.txt` | 改为优先 `/boot/firmware/config.txt`，旧系统可能是 `/boot/config.txt` |

### 10.5 开源文档建议写法

如果后续把本项目开源，建议 README 中明确声明：

```text
This project is an independent reverse-engineering and restoration effort for
21 Bitcoin Computer related hardware/software. It is not affiliated with 21 Inc.
Hardware protocol notes are based on local source inspection, public datasheets,
photos, and user measurements. Any unmeasured ASIC/HAT signal mapping must be
treated as provisional until verified with a logic analyzer or oscilloscope.
```

中文说明可写为：

```text
本项目是针对 21 Bitcoin Computer 相关硬件/软件的独立复原与二次开发资料，
与原厂 21 Inc. 无关联。文档中的硬件协议说明来自本地源码审计、公开数据手册、
照片分析和实测计划；凡未经过逻辑分析仪或示波器确认的 ASIC/HAT 信号映射，
均应视为待验证推测。
```

### 10.6 开源仓库建议结构

建议后续将项目整理为以下结构：

```text
21-bitcoin-computer-notes/
  README.md
  docs/
    development_log.md
    hardware_notes.md
    raspberry_pi_setup.md
    protocol_notes.md
    esp32_plan.md
    safety_checklist.md
    references.md
  scripts/
    example_wallet.py
    payment_api_demo.py
    monitor_minerd.py
  vendor/
    two1-3.10.9/
  images/
    hardware/
  captures/
    README.md
```

说明：

- `vendor/two1-3.10.9/` 放修复过的 `two1` 源码时，应单独保留原始包来源和 license 说明。
- 当前 `two1` 包元数据中 `PKG-INFO` 显示 `License: FreeBSD`，但 classifier 又写有 `MIT License`，开源前应进一步查找原仓库 LICENSE 文件或 PyPI 历史页面，避免许可证表述错误。
- 如果不确定许可证，建议不要把修改后的完整 `two1` 源码直接混入主仓库；可以先以 patch 文件形式发布，或在 README 中说明来源与许可证待核验。

### 10.7 后续仍需联网/实测确认的资料

| 待确认项 | 推荐方法 |
|---|---|
| 21 Bitcoin Computer 原始硬件资料、FCC、维修资料 | 搜索 FCC ID、板号、产品手册、历史论坛和归档网页 |
| ASIC 真实型号 | 查看芯片标记、拆散热器高清拍照、查丝印和封装 |
| HAT EEPROM 信息 | 在树莓派上读取 `/proc/device-tree/hat/product`、`/proc/device-tree/hat/uuid` |
| MCP23008 实际地址和寄存器初始化值 | 原机运行 `i2cdetect`、`i2cget`，并在启动前后对比 |
| 主通信协议 SPI/UART | 逻辑分析仪抓取 Pin 19/21/23/24 和 Pin 8/10，以及可疑测试点 |
| 电源拓扑 | 万用表/示波器测 DC 输入、3.3V、ASIC core、风扇电压 |
| 现代矿池适配方案 | 单独实现 Stratum client，不依赖已失效的 21.co 服务 |

### 10.8 当前开源可用结论

当前文档中可以作为开源资料稳定发布的内容：

- 树莓派 40-pin 候选引脚和安全注意事项。
- MCP23008 的通用寄存器表、I2C 地址规则、读写注意事项。
- `two1` 源码层面的 `minerd` socket、PID、默认 pool URL、HAT 检测路径。
- ESP32 替代控制板的分阶段开发路线。
- 逻辑分析仪抓包方案和风险清单。

当前必须标注为“待验证”的内容：

- 21 ASIC 主通信到底是 SPI、UART 还是其他时序。
- ASIC 型号、核心电压、I/O 电压。
- MCP23008 每个 GP 引脚具体控制对象。
- AVCH16T245 A/B 侧电压域和 `DIR/OE` 控制来源。
- 风扇控制、电源使能、温度保护逻辑。

---

## ✅ 第十一轮：树莓派 5 / ESP32 可用性推测与主控开发板推荐 (2026-06-16 14:45)

### 11.1 本轮结论先行

本轮问题是：这块 21 Bitcoin Computer HAT/矿机零件能不能在 **树莓派 5** 使用？能不能在 **ESP32** 使用？目前哪些主控开发板“最可靠、最可能驱动”？

结论必须分层说：

| 平台 | 当前能确定的能力 | 当前不能保证的能力 | 推荐程度 |
|---|---|---|---|
| 原机树莓派 / 原 21 Bitcoin Computer 系统 | 最可靠，可作为原始参考平台 | 原 21.co 云服务可能失效 | 最高 |
| Raspberry Pi 2/3/4 | 40-pin、I2C、SPI、UART 与原 HAT 形态最接近，适合作为 Linux 调试主机 | 需要确认 `minerd`、HAT EEPROM、依赖环境是否匹配 | 很高 |
| Raspberry Pi 5 | 40-pin GPIO 仍存在，I2C/SPI/UART 仍可用于抓包和自写程序控制 | 不能保证旧版 `minerd`/底层驱动无需修改即可运行 | 中高，适合开发，不适合直接假定兼容 |
| ESP32-S3 | 硬件资源足够做 I2C/SPI/UART、Wi-Fi、Stratum client、Web UI | 在 ASIC 协议未逆向前，不能保证直接驱动 ASIC 挖矿 | 适合二阶段开发 |
| 普通 ESP32-WROOM | 可做 I2C/SPI/UART 原型和简单控制 | GPIO/USB/调试体验不如 ESP32-S3；复杂协议和 Web UI 余量较小 | 可用但不是首选 |
| RP2040 / Raspberry Pi Pico | 可做 I2C/SPI/UART 时序实验，PIO 很适合协议复刻 | 无原生 Wi-Fi（Pico W 除外），不适合单板完整矿机控制 | 适合底层时序实验 |
| STM32 | 工业控制能力强，外设稳定 | 开发门槛更高，网络/Stratum/Web UI 需额外处理 | 适合有 STM32 经验者 |

最稳妥的开发顺序：

```text
原机树莓派抓包 -> Raspberry Pi 3/4 复现软件环境 -> ESP32-S3 复刻控制时序 -> 自研 PCB
```

### 11.2 Raspberry Pi 5 能不能用

#### 可以确定能做的事

Raspberry Pi 5 仍然适合作为开发和测试主机，原因如下：

- Raspberry Pi 官方文档确认当前板卡仍提供 40-pin GPIO header。
- 40-pin 上仍有常见 I2C、SPI0、UART 引脚功能。
- 普通 GPIO 仍是 3.3V 逻辑，适合接 HAT 主机侧信号。
- Linux 环境方便运行 Python、`i2c-tools`、逻辑分析仪辅助脚本、串口工具和网络服务。
- 对于 `i2cdetect`、`i2cget`、`spidev`、UART 抓包、`monitor_minerd.py` 这类开发/验证工作，Raspberry Pi 5 是可用平台。

#### 不能保证的事

不能直接写“Raspberry Pi 5 一定能原样运行 21 Bitcoin Computer HAT 挖矿”，原因：

- 原 21 Bitcoin Computer 软件时代早于 Raspberry Pi 5，旧 `minerd` 或 HAT 驱动可能依赖旧内核、旧设备树、旧用户态环境。
- Raspberry Pi 5 的底层 I/O 控制架构与旧 Pi 不完全相同，虽然 40-pin 接口兼容，但低层行为、设备树路径、默认串口映射、库兼容性都可能不同。
- 旧版 `two1` Python 依赖偏老，直接在 Raspberry Pi OS Bookworm / Python 3.11+ 上运行可能需要兼容修复。
- 如果 HAT 使用 EEPROM 自动识别，需确认 Pi 5 是否正确读取 `/proc/device-tree/hat/product` 与相关 overlay。

#### Raspberry Pi 5 推荐用途

| 用途 | 是否推荐 | 说明 |
|---|---|---|
| I2C 扫描 MCP23008 | 推荐 | 可用 `i2cdetect -y 1` 验证 |
| SPI/UART 被动抓包配合 | 推荐 | 逻辑分析仪仍应作为主要证据 |
| 运行 `example_wallet.py` | 推荐 | 取决于 Python 依赖修复 |
| 运行 `payment_api_demo.py` | 可行 | 需要钱包配置和 Flask/two1 依赖 |
| 运行原机 `minerd` | 待验证 | 不能开源承诺直接可用 |
| 作为最终矿机控制器 | 可作为候选 | 但成本和功耗高于 ESP32-S3 |

#### Raspberry Pi 5 使用方法

建议使用方式：

1. 安装 Raspberry Pi OS Lite 64-bit 或 32-bit。若目标是兼容旧 `two1`，32-bit 可能更省心。
2. 启用 SSH、I2C、SPI、UART。
3. 编辑 `/boot/firmware/config.txt`：

```text
dtparam=i2c_arm=on
dtparam=spi=on
enable_uart=1
```

4. 安装工具：

```bash
sudo apt update
sudo apt install -y i2c-tools python3-pip python3-venv git minicom screen lsof htop
```

5. 先只做非破坏性检查：

```bash
i2cdetect -y 1
ls /dev/spidev*
ls -l /dev/serial0 /dev/ttyAMA0 /dev/ttyS0
cat /proc/device-tree/hat/product 2>/dev/null
cat /proc/device-tree/hat/uuid 2>/dev/null
```

6. 如果能读到 HAT product 且 I2C 出现 `0x20`，再继续尝试运行本项目脚本。

重要原则：

- Raspberry Pi 5 可作为“开发主机/验证主机”。
- 是否能作为“原机无修改替代主机”，必须以实测为准。
- 开源 README 中应写“Raspberry Pi 5 likely usable for development and bus access, but original minerd compatibility is unverified”。

### 11.3 ESP32 能不能用

#### 可以确定能做的事

ESP32，尤其是 ESP32-S3，硬件上适合做新主控：

- ESP32-S3 有 3 个 UART、2 个 I2C、2 个通用 SPI 端口。
- ESP32-S3 有 Wi-Fi，可直接实现矿池连接、Web 配置页面和状态 API。
- ESP32-S3 为 3.3V 逻辑，适合连接 HAT 的树莓派主机侧信号。
- ESP32-S3 有 USB Serial/JTAG，调试体验好。
- 对 MCP23008 这类 I2C 外设，ESP32-S3 可以确定能驱动。
- 对复位、使能、LED、风扇 PWM 这类 GPIO 控制，ESP32-S3 可以确定能实现。

#### 不能保证的事

不能直接写“ESP32 现在一定能驱动 ASIC 挖矿”，原因：

- ASIC 主通信协议未确认。
- 初始化序列、寄存器、nonce 返回格式、work 格式均未知。
- AVCH16T245 的方向控制和电压域未确认。
- MCP23008 的每个 GP 引脚具体作用未确认。
- 现代 Stratum job 如何转换为该 ASIC 的 work 格式仍未知。

#### ESP32 推荐用途

| 阶段 | ESP32 能做什么 | 是否可立即做 |
|---|---|---|
| 阶段 1 | I2C 扫描 MCP23008、读写寄存器 | 可以 |
| 阶段 2 | 复刻 HAT reset/enable/LED/风扇控制 | 可以，但需先抓原机寄存器 |
| 阶段 3 | 复刻 UART/SPI 初始化包 | 需要逻辑分析仪抓包 |
| 阶段 4 | 发送固定测试 work，读取 nonce | 需要协议逆向 |
| 阶段 5 | 接现代 Stratum 矿池 | 需要底层 ASIC 协议先跑通 |
| 阶段 6 | 做完整独立矿机固件 | 可行，但不是第一步 |

### 11.4 ESP32-S3 推荐接线方法

建议先接 HAT 的 40-pin 主机侧，不要直接接 ASIC 裸信号侧。

| HAT/Raspberry Pi 物理引脚 | 功能候选 | ESP32-S3 建议连接 | 说明 |
|---|---|---|---|
| Pin 6/9/14/20/25/30/34/39 | GND | GND | 必须共地 |
| Pin 3 | I2C SDA | GPIO 8 或其他可用 GPIO | 先用于 MCP23008 |
| Pin 5 | I2C SCL | GPIO 9 或其他可用 GPIO | 先用于 MCP23008 |
| Pin 19 | SPI MOSI 候选 | 任意 SPI MOSI GPIO | 仅在确认 SPI 后接入 |
| Pin 21 | SPI MISO 候选 | 任意 SPI MISO GPIO | 仅在确认 SPI 后接入 |
| Pin 23 | SPI SCLK 候选 | 任意 SPI SCLK GPIO | 仅在确认 SPI 后接入 |
| Pin 24 | SPI CE0 候选 | 任意 GPIO | 仅在确认 SPI 后接入 |
| Pin 8 | UART TX 候选 | ESP32 RX | 先用高阻/串阻被动监听 |
| Pin 10 | UART RX 候选 | ESP32 TX | 未确认前不要主动发送 |

安全建议：

- 每条未知信号先串联 `100Ω-330Ω` 电阻。
- 未确认方向前，ESP32 引脚先配置为输入。
- HAT 继续使用原 DC Jack 供电，ESP32 使用 USB 供电，两者只共地。
- 不要从 ESP32 给 HAT 的 3.3V 或 5V 反向供电。
- 若发现 HAT 主机侧不是 3.3V，必须加电平转换。

### 11.5 ESP32-S3 最小可运行固件目标

第一版固件不追求挖矿，只追求安全确认硬件链路：

```text
boot
  -> print chip info
  -> init I2C
  -> scan bus
  -> find MCP23008
  -> read IODIR/IPOL/GPPU/GPIO/OLAT
  -> print register dump
  -> do not write outputs by default
```

第二版固件才增加可控写入：

```text
unlock command required
  -> write known-safe MCP23008 register values
  -> toggle one confirmed LED or reset line
  -> log every write
  -> allow emergency all-input state
```

第三版固件再做 ASIC transport：

```text
select transport = UART or SPI
  -> replay captured init sequence
  -> compare response bytes
  -> replay fixed work
  -> wait nonce/result
```

### 11.6 目前“一定能驱动”的主控开发板清单

这里的“一定能驱动”必须严格定义。当前在没有 ASIC 协议抓包的情况下，只有以下能力可以说“确定”：

- 能驱动 MCP23008：I2C 主机即可。
- 能控制 HAT 主机侧 GPIO：3.3V GPIO 主控即可。
- 能被动抓取/主动复刻 SPI/UART：具备 SPI/UART 的主控即可。
- 能完整驱动 ASIC 挖矿：目前只有原 21 Bitcoin Computer 原机环境最接近“已知可用”；其他板都必须逆向后才能确认。

因此按可靠度排序：

| 排名 | 主控/开发板 | 当前可靠结论 | 适合用途 | 推荐等级 |
|---|---|---|---|---|
| 1 | 原 21 Bitcoin Computer 原机树莓派与原系统 | 最有可能完整驱动 HAT/ASIC | 原始行为记录、抓包、验证 minerd | 必备 |
| 2 | Raspberry Pi 3B/3B+ | 40-pin、Linux、I2C/SPI/UART 成熟，形态接近旧系统 | 替代测试主机、运行脚本、抓包辅助 | 强烈推荐 |
| 3 | Raspberry Pi 4B | 性能更强，40-pin 兼容，资料多 | 开发主机、脚本运行、网络服务 | 推荐 |
| 4 | Raspberry Pi 2B | 与原时代接近 | 原机复古环境、旧系统兼容测试 | 推荐但性能较弱 |
| 5 | Raspberry Pi 5 | 现代性能强，40-pin 可用，但旧 minerd 兼容未验证 | 开发主机、总线测试、自写控制程序 | 推荐但需标注未验证 |
| 6 | ESP32-S3 DevKitC-1 / ESP32-S3-DevKit | 外设足够、Wi-Fi、USB 调试好 | 新主控固件、MCP23008、Web UI、Stratum client | 新主控首选 |
| 7 | ESP32-WROOM-32 DevKit | 资源够做原型 | I2C/SPI/UART 初步实验 | 可用 |
| 8 | Raspberry Pi Pico / Pico W | PIO 适合时序复刻 | 协议波形复刻、低层实验 | 辅助推荐 |
| 9 | STM32 Nucleo / Black Pill | 时序和工业外设强 | 严肃固件开发、低层协议实现 | 有经验再选 |

### 11.7 不推荐作为第一阶段主控的板子

| 板子 | 不推荐原因 |
|---|---|
| Arduino UNO/Nano 经典 AVR | 5V 逻辑风险、内存小、网络能力弱 |
| ESP8266 | GPIO 少、外设和内存紧张，不适合复杂协议和 Web/矿池 |
| Raspberry Pi Pico 非 W | 无网络，适合时序实验但不适合独立矿机 |
| Linux 小板但无 40-pin 标准接口 | 接线和驱动成本高，不利于复刻 |
| 任意 5V MCU 直连 HAT | 树莓派/HAT 主机侧按 3.3V 逻辑处理，5V 直连有损坏风险 |

### 11.8 推荐开发路线：树莓派 5 与 ESP32 怎么配合

最佳组合不是二选一，而是分工：

| 角色 | 推荐板 | 任务 |
|---|---|---|
| 原机参考 | 原 21 Bitcoin Computer / Pi 2 | 跑原软件、抓真实波形 |
| Linux 调试主机 | Raspberry Pi 3/4/5 | 读 HAT EEPROM、I2C、SPI、UART、运行 Python 工具 |
| 新主控原型 | ESP32-S3 | 复刻 I2C/GPIO/ASIC transport、做 Wi-Fi/Web/矿池 |
| 低层时序辅助 | Pico / RP2040 | 用 PIO 复刻特殊时序或辅助抓取 |

实际步骤：

1. 原机启动，保存 `/proc/device-tree/hat/product`、`hat/uuid`、`i2cdetect`、`minerd_events.log`。
2. 逻辑分析仪抓 I2C、SPI、UART 候选线。
3. Raspberry Pi 5 复现 I2C/SPI/UART 访问，不直接承诺旧 `minerd`。
4. ESP32-S3 先只读 MCP23008，不写。
5. 根据抓包确认 reset/enable 位后，ESP32-S3 复刻控制。
6. 根据抓包确认 SPI/UART 后，ESP32-S3 复刻 ASIC 初始化。
7. 读回 nonce 后，再开始现代 Stratum 对接。

### 11.9 树莓派 5 使用模板

```bash
sudo apt update
sudo apt install -y i2c-tools python3-pip python3-venv git minicom screen lsof htop
```

编辑：

```bash
sudo nano /boot/firmware/config.txt
```

添加或确认：

```text
dtparam=i2c_arm=on
dtparam=spi=on
enable_uart=1
```

重启后检查：

```bash
i2cdetect -y 1
ls /dev/spidev*
ls -l /dev/serial0 /dev/ttyAMA0 /dev/ttyS0
cat /proc/device-tree/hat/product 2>/dev/null
cat /proc/device-tree/hat/uuid 2>/dev/null
```

如果 `i2cdetect` 能看到 `0x20`，继续读 MCP23008：

```bash
i2cget -y 1 0x20 0x00
i2cget -y 1 0x20 0x09
i2cget -y 1 0x20 0x0A
```

### 11.10 ESP32-S3 使用模板

推荐工程：

- ESP-IDF 优先，Arduino 可做快速扫描，但不建议作为最终矿机固件。
- 分模块：`mcp23008`、`board_power`、`asic_transport`、`asic_protocol`、`stratum_client`、`web_status`。

第一阶段伪代码：

```c
void app_main(void) {
    board_init_uart_log();
    i2c_master_init();
    i2c_scan();

    if (mcp23008_probe(0x20)) {
        mcp23008_dump_registers(0x20);
    }

    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
```

第二阶段才允许写寄存器：

```c
if (user_confirmed_safe_write()) {
    mcp23008_write_reg(0x20, MCP23008_IODIR, known_iodir);
    mcp23008_write_reg(0x20, MCP23008_OLAT, known_olat);
}
```

开源时建议默认固件只读不写，避免用户一烧录就误触发 HAT 复位、电源或 ASIC 线。

### 11.11 可靠性等级定义

为了避免开源后误解，建议仓库中给每条硬件结论标注等级：

| 等级 | 含义 | 示例 |
|---|---|---|
| L0 已实机验证 | 已在本项目硬件上测量或运行成功 | `i2cdetect` 确认地址 |
| L1 源码确认 | two1 源码中明确存在 | `/tmp/minerd.sock` |
| L2 数据手册确认 | 器件官方文档确认 | MCP23008 寄存器 |
| L3 平台官方确认 | Raspberry Pi / Espressif 官方文档确认 | Pi 40-pin、ESP32-S3 I2C/SPI/UART |
| L4 照片推测 | 根据照片和丝印推断 | 某测试点用途 |
| L5 待验证假设 | 必须抓包或测量 | ASIC 主通信协议 |

本项目当前最重要的待验证项仍是：

```text
ASIC transport protocol = UNKNOWN
```

只要这个未知项没解决，所有“ESP32 直接挖矿”“树莓派 5 原样替代”的说法都必须保守处理。

---

## ✅ 第十二轮：实测模板、开发里程碑与开源协作资料补充 (2026-06-16 15:15)

### 12.1 本轮补充目标

本轮把前面的分析转换为更容易执行的工程清单，方便后续自己开发，也方便开源后让别人按统一格式贡献数据。

新增重点：

- 实测记录模板。
- 逻辑分析仪抓包记录模板。
- 树莓派 5、ESP32-S3、原机三平台的判定流程。
- ESP32-S3 最小固件开发里程碑。
- 开源 issue/PR 任务拆分。
- 不能越过的硬件安全红线。

### 12.2 实测资料总表模板

建议后续新建 `docs/hardware_notes.md`，按以下格式记录。没有实测的数据不要猜，写 `TBD`。

```markdown
# Hardware Notes

## Board Identity

| Item | Value | Evidence |
|---|---|---|
| Product name | 21 Bitcoin Computer HAT | photo / HAT EEPROM / TBD |
| Board marking | 830-0016 / Rev ? | photo |
| Serial number | TBD | sticker / photo |
| ASIC marking | TBD | macro photo |
| Main connector | Raspberry Pi 40-pin | visual |

## Power Rails

| Rail | Measured Voltage | Condition | Test Point | Notes |
|---|---:|---|---|---|
| DC input | TBD | idle | DC jack | |
| 5V | TBD | idle | TBD | |
| 3.3V logic | TBD | idle | TBD | |
| ASIC core | TBD | idle | inductor output / TBD | high-risk measurement |
| fan supply | TBD | fan running | fan connector | |

## Current

| State | Current | Input Voltage | Notes |
|---|---:|---:|---|
| HAT connected, minerd off | TBD | TBD | |
| minerd starting | TBD | TBD | |
| mining stable | TBD | TBD | |
| fan disconnected test | do not run unless needed | | |

## I2C

| Bus | Command | Result | Notes |
|---|---|---|---|
| i2c-1 | `i2cdetect -y 1` | TBD | expect MCP23008 if address pins match |

## MCP23008 Register Snapshots

| State | IODIR 0x00 | IPOL 0x01 | GPPU 0x06 | GPIO 0x09 | OLAT 0x0A | Notes |
|---|---|---|---|---|---|---|
| power on | TBD | TBD | TBD | TBD | TBD | |
| before minerd | TBD | TBD | TBD | TBD | TBD | |
| minerd running | TBD | TBD | TBD | TBD | TBD | |
| minerd stopped | TBD | TBD | TBD | TBD | TBD | |
```

### 12.3 抓包记录模板

建议新建 `docs/protocol_notes.md`，每次抓包都要写清楚环境。后续开源协作者也按这个格式提交，数据才可比较。

```markdown
# Protocol Notes

## Capture Metadata

| Item | Value |
|---|---|
| Capture file | captures/capture_YYYYMMDD_case.sal |
| Board | 21 Bitcoin Computer HAT |
| Host | Raspberry Pi model / OS |
| HAT power | voltage/current |
| Software state | idle / minerd start / mining / shutdown |
| Logic analyzer | model |
| Sample rate | MHz |
| Threshold | V |
| Channels | mapping table below |

## Channel Mapping

| LA Channel | Physical Pin / Test Point | Signal Guess | Voltage | Direction Guess |
|---|---|---|---|---|
| CH0 | GND | GND | 0V | reference |
| CH1 | Pin 3 | I2C SDA | 3.3V | bidirectional |
| CH2 | Pin 5 | I2C SCL | 3.3V | host to device |
| CH3 | Pin 19 | SPI MOSI candidate | TBD | host to HAT |
| CH4 | Pin 21 | SPI MISO candidate | TBD | HAT to host |
| CH5 | Pin 23 | SPI SCLK candidate | TBD | host to HAT |
| CH6 | Pin 24 | SPI CE0 candidate | TBD | host to HAT |
| CH7 | Pin 8/10 or TPxx | UART candidate | TBD | TBD |

## Decoded Results

| Time | Bus | Event | Data | Interpretation |
|---|---|---|---|---|
| 0.000s | I2C | write | TBD | TBD |
| 0.000s | SPI/UART | TBD | TBD | TBD |

## Findings

- Confirmed:
- Suspected:
- Unknown:
- Next capture:
```

### 12.4 树莓派 5 可用性判定流程

树莓派 5 是否能用于这块 HAT，不用争论，按以下步骤判定。

| 步骤 | 命令/动作 | 通过标准 | 失败时处理 |
|---|---|---|---|
| 1 | 正常启动 Pi 5 | SSH 可登录 | 先解决系统/供电 |
| 2 | 启用 I2C/SPI/UART | `/boot/firmware/config.txt` 配置生效 | 检查 config 与重启 |
| 3 | 插 HAT 但不启动 minerd | 无异常发热/掉电 | 断电检查短路与方向 |
| 4 | `cat /proc/device-tree/hat/product` | 能读到 HAT 信息更好 | 读不到不代表 HAT 不可用，继续手动测试 |
| 5 | `i2cdetect -y 1` | 出现预期 I2C 设备，如 `0x20` | 查 I2C、供电、地址脚 |
| 6 | `ls /dev/spidev*` | 出现 spidev 设备 | 检查 SPI 配置 |
| 7 | 逻辑分析仪被动监听 | 上电/运行时有总线活动 | 扩展抓取通道 |
| 8 | 运行本项目 Python 脚本 | 可导入/可监控 | 修 Python 依赖 |
| 9 | 尝试原 `minerd` | 能启动并产生 socket | 若失败，记录日志，不强行假定兼容 |

判定结果写法：

```text
Raspberry Pi 5 status:
- GPIO/I2C/SPI/UART access: PASS/FAIL
- HAT EEPROM read: PASS/FAIL/NOT PRESENT
- MCP23008 detection: PASS/FAIL
- original minerd compatibility: PASS/FAIL/UNTESTED
- safe for development: YES/NO
- safe as direct original replacement: YES/NO/UNKNOWN
```

### 12.5 ESP32-S3 可用性判定流程

ESP32-S3 的判定不能以“能不能挖矿”为第一步，而要按外设链路逐层推进。

| 阶段 | 目标 | 通过标准 | 输出资料 |
|---|---|---|---|
| E0 | 只接 GND，不接信号 | 无异常电流/发热 | 接线照片 |
| E1 | I2C 扫描 | 能找到 MCP23008 或确认无响应原因 | 串口日志 |
| E2 | 只读 MCP23008 | 能读 `IODIR/GPIO/OLAT` | register dump |
| E3 | 安全写 MCP23008 | 只改已确认安全位，如 LED | 前后寄存器和波形 |
| E4 | 复刻 reset/enable | HAT 行为与原机一致 | 对比波形 |
| E5 | SPI/UART 初始化回放 | ASIC 有预期响应 | 原始 bytes |
| E6 | 固定 work 测试 | 能收到 nonce/result | 测试向量 |
| E7 | Stratum 接入 | 能提交有效 share | 矿池日志 |

每一阶段都必须能回退到安全状态：

```text
all GPIO input
I2C no-write mode
transport disabled
fan forced on
ASIC reset asserted only if confirmed safe
```

### 12.6 ESP32-S3 固件安全开关设计

开源固件默认必须保守，避免用户直接烧录后误驱动硬件。

建议增加以下编译开关：

```c
#define ENABLE_I2C_SCAN_ONLY        1
#define ENABLE_MCP23008_WRITE       0
#define ENABLE_ASIC_TRANSPORT       0
#define ENABLE_CAPTURE_REPLAY       0
#define ENABLE_STRATUM_CLIENT       0
```

建议运行时也加命令确认：

```text
help
scan
dump mcp23008
unlock-write I_UNDERSTAND_THE_RISK
write-reg 0x20 0x0A 0x00
transport-enable I_HAVE_CAPTURED_THE_ORIGINAL_BUS
replay-init capture_02
```

这样开源后默认行为是“只读、可观察”，而不是“上电就控制 ASIC”。

### 12.7 最小测试向量规划

等抓包完成后，需要整理“测试向量”，让不同主控能复现同一段行为。

建议格式：

```markdown
## Test Vector: MCP23008 Init Sequence

Source capture: capture_02_minerd_start.sal
Host: original Raspberry Pi / original minerd

| Step | Bus | Operation | Address | Register | Value | Delay |
|---|---|---|---|---|---|---|
| 1 | I2C | write | 0x20 | 0x00 | TBD | TBD |
| 2 | I2C | write | 0x20 | 0x0A | TBD | TBD |

Expected result:
- LED:
- fan:
- ASIC reset:
- current:
```

ASIC transport 测试向量：

```markdown
## Test Vector: ASIC Init Replay

Transport: UART/SPI/TBD
Voltage: TBD
Speed: TBD
Mode: TBD

TX:
TBD

RX expected:
TBD

Timing:
TBD
```

### 12.8 建议新增脚本

后续可添加一些不会伤硬件的只读脚本：

| 脚本 | 平台 | 作用 |
|---|---|---|
| `scripts/raspi_collect_info.sh` | Raspberry Pi | 收集 HAT、I2C、SPI、UART、系统信息 |
| `scripts/read_mcp23008.py` | Raspberry Pi | 只读 MCP23008 寄存器 |
| `scripts/compare_mcp23008_snapshots.py` | PC/Raspberry Pi | 对比启动前后寄存器变化 |
| `scripts/minerd_event_logger.py` | Raspberry Pi | 保存原始 socket JSON |
| `firmware/esp32_s3_i2c_probe/` | ESP32-S3 | 只读 I2C 扫描与寄存器 dump |

`raspi_collect_info.sh` 建议采集：

```bash
uname -a
cat /etc/os-release
cat /proc/device-tree/hat/product 2>/dev/null
cat /proc/device-tree/hat/uuid 2>/dev/null
i2cdetect -y 1
ls /dev/spidev* 2>/dev/null
ls -l /dev/serial0 /dev/ttyAMA0 /dev/ttyS0 2>/dev/null
ps aux | grep minerd
ls -l /tmp/minerd.sock /run/minerd.pid 2>/dev/null
```

### 12.9 开源 Issue 任务拆分

建议开源后建立以下 Issues，让协作者按任务贡献：

| Issue 标题 | 目标 | 输出 |
|---|---|---|
| `Collect Raspberry Pi HAT EEPROM data` | 收集 `/proc/device-tree/hat/*` | 文本日志 |
| `Measure HAT power rails` | 测 DC/5V/3.3V/ASIC core/fan | 表格和照片 |
| `Capture I2C during minerd startup` | 抓 MCP23008 初始化 | `.sal` + 解码表 |
| `Identify MCP23008 GP pin functions` | 确认 GP0-GP7 连接对象 | 引脚功能表 |
| `Capture candidate SPI bus` | 判断 SPI 是否主通信 | 波形和解码 |
| `Capture candidate UART bus` | 判断 UART 是否主通信 | 波形和波特率 |
| `Confirm AVCH16T245 voltage domains` | 测 A/B 侧电压和 DIR/OE | 测量表 |
| `Build ESP32-S3 read-only probe firmware` | 做只读固件 | 源码和日志 |
| `Replay MCP23008 init on ESP32-S3` | 复刻安全控制线 | 对比视频/波形 |
| `Document license status of two1 vendor code` | 查清 two1 许可证 | LICENSE 说明 |

### 12.10 开源 PR 验收标准

为保证资料可靠，建议 PR 合并规则如下：

- 任何硬件结论必须附证据：照片、波形、命令输出、数据手册链接或源码位置。
- 任何“已确认”结论必须标注可靠性等级 L0-L3。
- L4/L5 内容必须明确写“推测”或“待验证”。
- 不接受“我感觉”“应该是”作为最终结论。
- 修改接线、供电、写寄存器相关内容时，必须附安全警告。
- 固件 PR 默认不得开启危险写操作。
- 波形文件要附通道映射和采样率。

### 12.11 硬件安全红线

以下操作在未确认前不要做：

| 禁止操作 | 原因 |
|---|---|
| 用 5V MCU GPIO 直连 HAT 信号 | 可能损坏树莓派侧或 HAT 逻辑 |
| 未测电压就把 ESP32 接到测试点 | 测试点可能不是 3.3V |
| 未确认 MCP23008 位功能就批量写 `GPIO/OLAT` | 可能错误切换 reset/enable/power |
| 未确认方向就让 ESP32 主动驱动 MISO/RX 类信号 | 可能与 HAT 输出冲突 |
| 拆散热器后长时间上电 | ASIC 可能快速过热 |
| 风扇不转时启动挖矿 | 过热风险 |
| HAT 接 DC Jack 时再从外部强灌 5V/3.3V | 反灌和稳压器冲突 |
| 把未知 ASIC core 电压短接到示波器地夹错误位置 | 有短路风险 |

### 12.12 当前最可靠的开发判断

截至本轮资料状态，最可靠的判断是：

```text
1. 原机树莓派/原系统是唯一最值得信任的参考行为来源。
2. Raspberry Pi 5 可以作为现代开发主机和总线测试平台，但不能承诺旧 minerd 原样兼容。
3. ESP32-S3 是最推荐的新主控原型平台，但当前只能保证 I2C/GPIO/transport 能力，不能保证 ASIC 挖矿。
4. 真正决定项目成败的不是主控算力，而是 ASIC transport protocol 的抓包和复刻。
5. 开源文档必须坚持证据分级，否则后续协作者容易被错误假设带偏。
```

---

## ✅ 第十三轮：开源仓库落地资料、README 草案与测试清单 (2026-06-16 15:45)

### 13.1 本轮补充目标

本轮继续把项目从“个人研究记录”推进到“可以开源协作”的结构：

- README 草案。
- 仓库目录落地方案。
- 引用资料与许可证说明。
- BOM 草案。
- 实验设备清单。
- 树莓派和 ESP32-S3 的第一批可执行命令。
- 测试清单。
- 贡献规范。
- 数据命名规则。

### 13.2 README 草案

后续开源时，`README.md` 可以按以下结构写：

```markdown
# 21 Bitcoin Computer Hardware Restoration Notes

This repository documents an independent restoration, reverse-engineering,
and modern-controller exploration effort for 21 Bitcoin Computer related
hardware and software.

## Status

Current status: research and measurement phase.

What is confirmed:

- Raspberry Pi 40-pin candidate pins are documented.
- MCP23008 register map is documented from the official datasheet.
- `two1` source confirms `/tmp/minerd.sock`, `/run/minerd.pid`, and
  `swirl+tcp://grid.21.co:21006`.
- ESP32-S3 is suitable as a candidate modern controller for I2C/SPI/UART
  experiments.

What is not confirmed:

- ASIC transport protocol.
- ASIC model.
- ASIC core voltage.
- MCP23008 GP0-GP7 exact board functions.
- AVCH16T245 A/B voltage domains and DIR/OE control source.

## Safety

Do not connect 5V GPIO to the HAT.
Do not write MCP23008 outputs until each bit function is known.
Do not assume SPI or UART before logic-analyzer capture.
Do not power the ASIC without proper cooling.

## Recommended Workflow

1. Run original hardware and collect logs.
2. Capture I2C/SPI/UART candidates with a logic analyzer.
3. Identify reset/enable/power/fan control pins.
4. Build ESP32-S3 read-only probe firmware.
5. Replay known-safe control sequences.
6. Reverse ASIC transport.
7. Only then implement mining/Stratum support.

## Reliability Levels

- L0: verified on actual hardware
- L1: confirmed from local source code
- L2: confirmed from component datasheet
- L3: confirmed from platform documentation
- L4: inferred from photo/board inspection
- L5: hypothesis, pending measurement

## Disclaimer

This project is independent and is not affiliated with 21 Inc.
Unverified hardware mappings must be treated as provisional.
```

### 13.3 推荐仓库目录落地方案

建议不要把所有内容都堆在 `development_log.md`，开源前拆成以下结构：

```text
21-bitcoin-computer-hat/
  README.md
  LICENSE
  docs/
    development_log.md
    hardware_notes.md
    raspberry_pi_setup.md
    raspberry_pi_5_notes.md
    esp32_s3_plan.md
    protocol_notes.md
    safety_checklist.md
    references.md
    reliability_levels.md
    open_questions.md
  scripts/
    example_wallet.py
    payment_api_demo.py
    monitor_minerd.py
    raspi_collect_info.sh
    read_mcp23008.py
  firmware/
    esp32_s3_i2c_probe/
      README.md
      main/
        CMakeLists.txt
        app_main.c
        mcp23008.c
        mcp23008.h
  captures/
    README.md
    raw/
    decoded/
  images/
    hardware/
    annotated/
  vendor/
    README.md
    patches/
```

目录原则：

- `docs/` 放人读的资料。
- `scripts/` 放树莓派/PC 脚本。
- `firmware/` 放 ESP32-S3 等新主控固件。
- `captures/` 放逻辑分析仪数据，原始文件和解码结果分开。
- `vendor/` 不直接塞不明许可证源码，优先放 patch 和来源说明。

### 13.4 许可证与合规说明

开源时要分清三类许可证：

| 内容 | 建议许可证/处理方式 | 说明 |
|---|---|---|
| 自己写的文档 | CC BY 4.0 或 CC BY-SA 4.0 | 方便别人引用 |
| 自己写的脚本/固件 | MIT / Apache-2.0 / GPL-3.0 三选一 | 若想最大兼容，MIT 最简单 |
| `two1` 原始源码 | 单独核验原始许可证 | 当前本地包元数据存在 `FreeBSD` 与 `MIT` 不一致 |
| 数据手册 PDF | 不要复制进仓库 | 只放官方链接 |
| 图片 | 自己拍摄可自定授权；网络图需谨慎 | 确认来源 |
| 逻辑分析仪抓包 | 自己采集可开源 | 注意不要包含私钥/账户/token |

建议：

```text
Documentation: CC BY-SA 4.0
Original scripts and firmware: MIT
Vendor code: not included by default; patches only until license is verified
```

### 13.5 `references.md` 草案

```markdown
# References

## Official Platform Docs

- Raspberry Pi computer hardware documentation:
  https://www.raspberrypi.com/documentation/computers/raspberry-pi.html
- Raspberry Pi configuration documentation:
  https://www.raspberrypi.com/documentation/computers/configuration.html
- Espressif ESP32-S3 datasheet:
  https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf

## Component Datasheets

- Microchip MCP23008/MCP23S08 datasheet:
  https://ww1.microchip.com/downloads/aemDocuments/documents/APID/ProductDocuments/DataSheets/MCP23008-and-MCP23008-Data-Sheet-DS20001919.pdf
- TI SN74AVCH16T245 datasheet:
  https://www.ti.com/lit/ds/symlink/sn74avch16t245.pdf

## Related Open Source Mining Projects

- ESP-Miner:
  https://github.com/bitaxeorg/ESP-Miner
- Bitaxe hardware:
  https://github.com/bitaxeorg/bitaxe

## Local Source Evidence

- `two1_source/two1-3.10.9/two1/__init__.py`
- `two1_source/two1-3.10.9/two1/commands/mine.py`
- `two1_source/two1-3.10.9/two1/commands/util/bitcoin_computer.py`
```

### 13.6 BOM 草案

这个 BOM 不是最终自研板 BOM，而是开发和验证阶段的工具/材料清单。

| 类别 | 推荐项 | 用途 | 必需程度 |
|---|---|---|---|
| 原始硬件 | 21 Bitcoin Computer / HAT | 参考对象 | 必需 |
| Linux 主机 | Raspberry Pi 3B/4B/5 | 运行脚本和总线测试 | 必需 |
| 新主控 | ESP32-S3 DevKitC-1 或同类 | 新固件原型 | 必需 |
| 逻辑分析仪 | 8 通道以上，建议 50MHz+ | 判断 SPI/UART/I2C | 必需 |
| 万用表 | 带电压/电阻/电流测量 | 电源和短路检查 | 必需 |
| 可调电源 | 带限流 | 安全上电 | 强烈推荐 |
| 示波器 | 50MHz+ | 电源纹波/高速波形 | 推荐 |
| 杜邦线 | 公母/母母 | 飞线原型 | 必需 |
| 串联电阻 | 100Ω、220Ω、330Ω | 未知 GPIO 限流 | 必需 |
| I2C 上拉电阻 | 2.2kΩ、4.7kΩ、10kΩ | 调试总线 | 推荐 |
| 散热工具 | 风扇、导热垫、温度计 | ASIC 保护 | 必需 |
| 热像仪/温度计 | 红外温度计或热像仪 | 热风险观察 | 推荐 |

### 13.7 树莓派脚本：`raspi_collect_info.sh` 草案

后续可把下面内容保存为 `scripts/raspi_collect_info.sh`：

```bash
#!/usr/bin/env bash
set -u

OUT_DIR="${1:-raspi_collect_$(date +%Y%m%d_%H%M%S)}"
mkdir -p "$OUT_DIR"

uname -a > "$OUT_DIR/uname.txt" 2>&1
cat /etc/os-release > "$OUT_DIR/os-release.txt" 2>&1

cat /proc/device-tree/hat/product > "$OUT_DIR/hat_product.txt" 2>&1 || true
cat /proc/device-tree/hat/uuid > "$OUT_DIR/hat_uuid.txt" 2>&1 || true
cat /proc/device-tree/hat/vendor > "$OUT_DIR/hat_vendor.txt" 2>&1 || true

i2cdetect -y 1 > "$OUT_DIR/i2cdetect_y_1.txt" 2>&1 || true
ls /dev/spidev* > "$OUT_DIR/spidev.txt" 2>&1 || true
ls -l /dev/serial0 /dev/ttyAMA0 /dev/ttyS0 > "$OUT_DIR/serial_devices.txt" 2>&1 || true

ps aux | grep minerd > "$OUT_DIR/minerd_process.txt" 2>&1 || true
ls -l /tmp/minerd.sock /run/minerd.pid > "$OUT_DIR/minerd_files.txt" 2>&1 || true

dmesg > "$OUT_DIR/dmesg.txt" 2>&1 || true
echo "Collected into $OUT_DIR"
```

### 13.8 MCP23008 只读脚本草案

后续可新增 `scripts/read_mcp23008.py`，用于只读寄存器，避免误写：

```python
#!/usr/bin/env python3
import subprocess

BUS = "1"
ADDR = "0x20"

REGS = [
    ("IODIR", "0x00"),
    ("IPOL", "0x01"),
    ("GPINTEN", "0x02"),
    ("DEFVAL", "0x03"),
    ("INTCON", "0x04"),
    ("IOCON", "0x05"),
    ("GPPU", "0x06"),
    ("INTF", "0x07"),
    ("INTCAP", "0x08"),
    ("GPIO", "0x09"),
    ("OLAT", "0x0A"),
]

def read_reg(reg):
    cmd = ["i2cget", "-y", BUS, ADDR, reg]
    return subprocess.check_output(cmd, text=True).strip()

for name, reg in REGS:
    try:
        print(f"{name:8s} {reg}: {read_reg(reg)}")
    except Exception as exc:
        print(f"{name:8s} {reg}: ERROR {exc}")
```

### 13.9 ESP32-S3 I2C Probe 工程验收标准

第一版 ESP32-S3 固件必须满足：

| 要求 | 标准 |
|---|---|
| 默认只读 | 不写 MCP23008，不拉任何未知 GPIO |
| 串口日志 | 输出芯片信息、I2C 扫描结果、寄存器 dump |
| 地址可配置 | 支持 `0x20`，也允许扫描 `0x20-0x27` |
| 错误清晰 | 无设备时输出 `MCP23008 not found` |
| 无阻塞危险操作 | 不自动进入 replay、不自动写 OLAT |
| 版本标识 | 输出 firmware version 和 git commit |

ESP32-S3 日志示例：

```text
21-hat-probe v0.1.0
mode: read-only
i2c scan:
  found: 0x20
mcp23008 dump:
  IODIR  0x00 = 0xff
  IPOL   0x01 = 0x00
  GPPU   0x06 = 0x00
  GPIO   0x09 = 0x00
  OLAT   0x0a = 0x00
write support: disabled
```

### 13.10 开发阶段里程碑

| 里程碑 | 目标 | 完成标准 |
|---|---|---|
| M0 | 资料整理 | README、references、safety 完成 |
| M1 | 原机资料采集 | HAT EEPROM、I2C、minerd socket 日志保存 |
| M2 | 电源测量 | DC/5V/3.3V/ASIC core/fan 电压记录 |
| M3 | I2C 抓包 | MCP23008 初始化序列明确 |
| M4 | MCP23008 引脚功能 | GP0-GP7 对应对象基本明确 |
| M5 | 主通信判断 | SPI/UART/其他协议明确 |
| M6 | ESP32-S3 只读固件 | 能稳定 dump MCP23008 |
| M7 | ESP32-S3 控制线复刻 | reset/enable/LED/风扇安全复刻 |
| M8 | ASIC 初始化回放 | 能得到 ASIC 响应 |
| M9 | 固定 work 测试 | 能得到 nonce/result |
| M10 | 矿池适配 | 能提交有效 share |
| M11 | 自研 PCB | 原型板可复现 M9/M10 |

### 13.11 数据文件命名规则

统一命名，后面才不会乱：

```text
YYYYMMDD_board_host_case.ext
```

示例：

```text
20260616_21hat_pi2_power_on_idle.sal
20260616_21hat_pi2_minerd_start_i2c.csv
20260616_21hat_pi5_i2cdetect.txt
20260616_21hat_esp32s3_mcp23008_dump.txt
20260616_21hat_power_measurements.md
```

字段说明：

| 字段 | 示例 | 说明 |
|---|---|---|
| 日期 | `20260616` | 采集日期 |
| board | `21hat` | 硬件对象 |
| host | `pi2` / `pi5` / `esp32s3` | 主控/采集平台 |
| case | `minerd_start_i2c` | 场景 |
| ext | `.sal` / `.csv` / `.txt` / `.md` | 文件类型 |

### 13.12 术语表

| 术语 | 说明 |
|---|---|
| HAT | Raspberry Pi 叠加板，本项目中指 21 Bitcoin Computer 矿机扩展板 |
| ASIC | 专用芯片，本项目中指 SHA-256 挖矿芯片 |
| MCP23008 | Microchip I2C 8-bit I/O 扩展器 |
| AVCH16T245 | 双电源总线收发/电平转换器系列 |
| `minerd` | 21 Bitcoin Computer 原系统中的矿工守护进程 |
| `swirl+tcp` | two1 原系统使用的矿池 URL scheme |
| Stratum | 现代比特币矿池常见协议 |
| nonce | 挖矿计算返回的候选随机数 |
| work/job | 矿池或主机下发给 ASIC 的计算任务 |
| transport | 底层物理/链路通信方式，如 SPI、UART |
| replay | 将原机抓包得到的初始化序列在新主控上重放 |

### 13.13 “不要做”的开源警告块

README 顶部建议放这个醒目的警告：

```markdown
> [!WARNING]
> This project involves powered hardware, unknown ASIC voltage domains,
> and unverified signal mappings. Do not connect 5V GPIO, do not write
> MCP23008 output registers, and do not replay bus traffic until you have
> verified voltage levels and signal direction on your own hardware.
```

中文版本：

```markdown
> [!WARNING]
> 本项目涉及带电硬件、未知 ASIC 电压域和未完全确认的信号映射。
> 未测量电压前不要接线，未确认位功能前不要写 MCP23008 输出寄存器，
> 未确认方向前不要主动驱动 SPI/UART 候选信号。
```

### 13.14 下一步最值得做的实际工作

下一步不要再扩散太多方向，优先做这 5 件事：

1. 拍 ASIC、U1、U12、DC 电源区域、40-pin 接口的高清近照并标注。
2. 用树莓派读取 `/proc/device-tree/hat/product`、`hat/uuid`。
3. 用 `i2cdetect -y 1` 确认 MCP23008 实际地址。
4. 读 MCP23008 的 `IODIR/GPIO/OLAT`，记录上电、minerd 前、minerd 后三个状态。
5. 抓一次 `minerd` 启动 10 秒内的 I2C/SPI/UART 候选线波形。

只有这 5 件完成后，ESP32-S3 的写控制和 ASIC 协议复刻才真正有依据。

---

## ✅ 第十四轮：硬件标注、引脚追踪与板级逆向方法 (2026-06-16 16:05)

### 14.1 本轮补充目标

本轮补充“怎么从照片和实物板一步步追出电路”的方法。目标是让后续资料不只停留在推测，而能逐步变成可验证的原理图。

重点：

- 照片标注方法。
- 芯片编号与封装识别。
- 万用表通断档追线流程。
- MCP23008 GP0-GP7 功能确认方法。
- AVCH16T245 A/B 侧和 DIR/OE 确认方法。
- 40-pin 到芯片的连接表。
- 测试点命名和记录规范。

### 14.2 图片标注建议

建议把 `图片/` 中 6 张照片复制到 `images/annotated/`，用任意图片编辑工具标注以下内容：

| 标注对象 | 标注格式 | 示例 |
|---|---|---|
| 芯片 | `U编号: 型号` | `U12: MCP23008` |
| 接口 | `J编号: 用途` | `J2: Raspberry Pi 40-pin` |
| 测试点 | `TP编号` | `TP49` |
| 电源 | `Rail name` | `3V3?`, `VIN?`, `ASIC_CORE?` |
| 信号 | `Signal?` | `SDA?`, `SCL?`, `RESET?` |
| 未确认 | 加 `?` | `UART_TX?` |

标注规则：

- 已经由丝印确认的不用 `?`。
- 由照片推测的必须加 `?`。
- 由万用表通断确认的可以写 `confirmed by continuity`。
- 由逻辑分析仪确认的可以写 `confirmed by capture`。

### 14.3 芯片识别表模板

建议新建 `docs/chip_inventory.md`：

```markdown
# Chip Inventory

| Ref | Marking | Guessed Part | Package | Evidence | Confidence |
|---|---|---|---|---|---|
| U12 | MCP23008? | MCP23008 | SSOP/QFN/TBD | photo marking | L4/L2 after confirmed |
| U1 | AVCH16T245? | SN74AVCH16T245 or compatible | TSSOP/TBD | photo marking | L4 |
| U15 | TBD | ASIC | TBD | photo | L5 |
| U? | TBD | regulator | TBD | board area | L5 |
```

Confidence 使用前面定义的 L0-L5。

### 14.4 万用表通断档追线流程

追线前必须断电，断开所有电源。

推荐流程：

1. 拍清晰正反面照片。
2. 标出 40-pin 每个物理引脚。
3. 用万用表通断档从 40-pin 引脚追到芯片引脚/测试点。
4. 一次只追一条线，记录“确定连通”和“不连通”。
5. 对 GND、3.3V、5V 先建立电源网络。
6. 对 I2C/SPI/UART 候选线再追到 U1/U12/ASIC 区域。

记录模板：

```markdown
## Continuity Test

Board state: unpowered
Meter: model
Date:

| From | To | Result | Resistance | Notes |
|---|---|---|---:|---|
| 40-pin Pin 3 | U12 SDA | connected | TBD ohm | confirmed I2C SDA |
| 40-pin Pin 5 | U12 SCL | connected | TBD ohm | confirmed I2C SCL |
| 40-pin Pin 19 | U1 A? | connected/TBD | TBD | SPI MOSI candidate |
| 40-pin Pin 24 | U1 A? | connected/TBD | TBD | SPI CE0 candidate |
```

### 14.5 40-pin 到板载器件连接表

最终需要形成这个表：

| 40-pin 物理引脚 | BCM | 标准功能 | 实测连接到 | 方向 | 可靠性 |
|---|---|---|---|---|---|
| Pin 3 | GPIO2 | SDA | U12 SCL/SDA TBD | bidirectional | L0 after continuity |
| Pin 5 | GPIO3 | SCL | U12 SCL/SDA TBD | host out | L0 after continuity |
| Pin 8 | GPIO14 | UART TX | TBD | host out | L5 |
| Pin 10 | GPIO15 | UART RX | TBD | host in | L5 |
| Pin 19 | GPIO10 | SPI MOSI | TBD | host out | L5 |
| Pin 21 | GPIO9 | SPI MISO | TBD | host in | L5 |
| Pin 23 | GPIO11 | SPI SCLK | TBD | host out | L5 |
| Pin 24 | GPIO8 | SPI CE0 | TBD | host out | L5 |

注意：表中的 `U12 SCL/SDA TBD` 需要最终按真实芯片引脚修正，不要靠目测永久定稿。

### 14.6 MCP23008 GP0-GP7 功能确认方法

MCP23008 的 GP 引脚功能不能靠猜，要按以下步骤确认：

1. 断电状态下，用通断档追 GP0-GP7 到其他元件、测试点、U1、ASIC、LED、电阻。
2. 上电但不运行 `minerd`，读取 `IODIR/GPIO/OLAT`。
3. 启动 `minerd` 前后重复读取寄存器。
4. 逻辑分析仪抓 I2C，记录 `IODIR/OLAT/GPIO` 写入变化。
5. 如果某个位随启动变化，再观察板上 LED、风扇、电流、ASIC reset 状态。
6. 只有在确认该位连接对象后，才允许 ESP32-S3 写该位。

建议记录：

```markdown
| GP Pin | Connected To | Direction | Idle | minerd start | Function Guess | Evidence |
|---|---|---|---|---|---|---|
| GP0 | TBD | TBD | TBD | TBD | reset? | L5 |
| GP1 | TBD | TBD | TBD | TBD | enable? | L5 |
| GP2 | TBD | TBD | TBD | TBD | LED? | L5 |
| GP3 | TBD | TBD | TBD | TBD | fan? | L5 |
| GP4 | TBD | TBD | TBD | TBD | interrupt? | L5 |
| GP5 | TBD | TBD | TBD | TBD | TBD | L5 |
| GP6 | TBD | TBD | TBD | TBD | TBD | L5 |
| GP7 | TBD | output only | TBD | TBD | TBD | datasheet + board |
```

### 14.7 AVCH16T245 方向与电压域确认方法

AVCH16T245 类器件必须确认三件事：

- A 侧接哪个电压。
- B 侧接哪个电压。
- `DIR` 和 `OE` 由谁控制。

断电追线：

| 引脚/网络 | 追踪目标 |
|---|---|
| VCCA | 测是否连到 3.3V 或 ASIC I/O 电压 |
| VCCB | 测是否连到 3.3V 或 ASIC I/O 电压 |
| GND | 确认地 |
| DIR | 追到固定上拉/下拉、MCP23008、树莓派 GPIO 或其他逻辑 |
| OE | 追到固定上拉/下拉、MCP23008、树莓派 GPIO 或电源管理 |
| A bus | 追到 40-pin 或主机侧 |
| B bus | 追到 ASIC 或矿片侧 |

上电测量：

```markdown
| Signal | Voltage idle | Voltage minerd | Notes |
|---|---:|---:|---|
| VCCA | TBD | TBD | |
| VCCB | TBD | TBD | |
| DIR | TBD | TBD | |
| OE | TBD | TBD | active low likely, confirm |
```

如果 `OE` 高电平，输出高阻；如果 `OE` 低电平，则根据 `DIR` 决定 A->B 或 B->A。实际逻辑必须按板上接法和数据手册确认。

### 14.8 测试点记录规范

测试点很多时，必须统一编号和照片位置。

模板：

```markdown
# Test Points

| TP | Location Photo | Connected Net | Voltage Idle | Voltage Mining | Signal Type | Evidence |
|---|---|---|---:|---:|---|---|
| TP1 | image_x annotated | GND? | 0V | 0V | ground | continuity |
| TP25 | image_x annotated | TBD | TBD | TBD | TBD | photo |
| TP49 | image_x annotated | I2C/SPI? | TBD | TBD | digital | TBD |
```

测试点分类：

| 类型 | 判断方法 |
|---|---|
| GND | 与电源地通断 |
| 电源 | 上电后稳定 DC 电压 |
| 数字信号 | 逻辑分析仪可见跳变 |
| 模拟/反馈 | 电压随状态变化但非数字方波 |
| 未知 | 暂不连接主控 |

### 14.9 电源拓扑逆向方法

电源是最容易损坏硬件的部分，先低风险记录：

1. 断电，测 DC Jack 正负极和 GND。
2. 断电，找大电感、稳压芯片、二极管、保险丝。
3. 上电限流，测 DC 输入。
4. 测 5V、3.3V、ASIC core、电平转换器 VCCA/VCCB。
5. 记录 idle/minerd start/mining 三个状态电压。
6. 如果电压掉落，记录电流和温升。

电源表模板：

```markdown
| Rail | Source Component | Test Point | Idle | minerd start | mining | Notes |
|---|---|---|---:|---:|---:|---|
| VIN | DC Jack | jack + | TBD | TBD | TBD | |
| 5V | regulator? | TBD | TBD | TBD | TBD | |
| 3V3 | regulator? | TBD | TBD | TBD | TBD | |
| ASIC_CORE | buck? | inductor output? | TBD | TBD | TBD | high current |
| FAN | fan connector | fan + | TBD | TBD | TBD | |
```

### 14.10 ASIC 识别方法

ASIC 型号必须谨慎确认。建议按以下顺序：

1. 不拆散热器时，从现有照片找芯片标记。
2. 如果必须拆散热器，先确认有替换导热材料。
3. 拆下后拍摄芯片正面高清照片。
4. 记录所有丝印、二维码、批号、封装尺寸。
5. 查同年代 21 Inc、Bitmain、Intel/21BC1 相关资料。
6. 不要因为“类似 BM1385/BM1366”就认定协议相同。

记录模板：

```markdown
| Field | Value |
|---|---|
| Package size | TBD |
| Marking line 1 | TBD |
| Marking line 2 | TBD |
| Date code | TBD |
| QR/DataMatrix | TBD |
| Similar known ASIC | TBD |
| Confidence | L5 until confirmed |
```

### 14.11 从抓包到协议文档的转换流程

抓包后不要急着写固件，先整理：

1. 分离 I2C、SPI、UART 通道。
2. 对每个 bus 做协议解码。
3. 找启动固定序列。
4. 找状态变化对应的写寄存器。
5. 找周期性心跳或轮询。
6. 找 work 下发和 nonce 返回边界。
7. 把原始字节保存为测试向量。
8. 用 Python 写一个离线 parser 验证格式。
9. 再移植到 ESP32-S3。

协议文档最终结构：

```markdown
# ASIC Protocol Notes

## Transport
- UART/SPI/TBD
- Speed:
- Mode:
- Voltage:
- Direction:

## Initialization Sequence

## Work Format

## Response Format

## Error/Status Frames

## Timing Requirements

## Test Vectors
```

### 14.12 本轮可执行任务

下一次实操建议直接做：

1. 标注 `image_editor_1781509820096.jpg`：40-pin、U12、U1、DC Jack、测试点。
2. 标注 `image_editor_1781509835478.jpg`：U12、U1 附近信号和测试点。
3. 用万用表确认 Pin 3/5 是否到 U12 的 SDA/SCL。
4. 用万用表确认 Pin 19/21/23/24 是否进入 U1 或 ASIC 区域。
5. 测 U1 的 VCCA/VCCB。
6. 读取 MCP23008 寄存器。
7. 开始第一份 `hardware_notes.md`。

---

## ✅ 第十五轮：首日/首周实操计划与任务拆解 (2026-06-16 16:30)

### 15.1 本轮目标

本轮把前面所有资料压缩成“可以直接照着做”的执行计划。适合你真正拿到树莓派、ESP32-S3、逻辑分析仪和万用表后开工。

核心原则：

```text
先无损观察 -> 再只读采集 -> 再被动抓包 -> 再有限写入 -> 最后协议复刻
```

### 15.2 首日计划：不写、不改、不冒险

首日目标不是驱动 ASIC，而是确认硬件身份、供电安全、I2C 是否可见。

| 顺序 | 任务 | 工具 | 输出文件 |
|---|---|---|---|
| 1 | 拍摄高清照片：正面、背面、局部芯片、电源、40-pin | 手机/相机 | `images/hardware/raw/` |
| 2 | 标注照片中的 U1、U12、U15、J、TP | 图片编辑工具 | `images/annotated/` |
| 3 | 断电测 5V/3.3V/GND 是否短路 | 万用表 | `docs/hardware_notes.md` |
| 4 | 树莓派不接 HAT 启动，确认系统正常 | Raspberry Pi | `raspi_collect_no_hat/` |
| 5 | 接 HAT，不启动 minerd，只读 HAT EEPROM/I2C | Raspberry Pi | `raspi_collect_hat_idle/` |
| 6 | 运行 `i2cdetect -y 1` | Raspberry Pi | `i2cdetect_y_1.txt` |
| 7 | 如果出现 `0x20`，只读 MCP23008 寄存器 | `i2cget` | `mcp23008_idle.txt` |
| 8 | 记录上电电流、发热、风扇状态 | 电源/温度计 | `power_measurements.md` |

首日禁止：

- 不启动挖矿。
- 不写 MCP23008。
- 不把 ESP32 接上 HAT。
- 不拆散热器。
- 不主动驱动任何未知信号。

### 15.3 首周计划：从只读到抓包

首周目标是拿到足够证据，判断 ASIC 主通信到底是 SPI、UART 还是其他。

| 天数 | 目标 | 任务 |
|---|---|---|
| Day 1 | 基线采集 | 完成首日计划 |
| Day 2 | 原机/树莓派状态 | 读取 HAT EEPROM、GPIO、I2C、系统日志 |
| Day 3 | minerd 监控 | 启动 `minerd`，保存 `/tmp/minerd.sock` 事件 |
| Day 4 | I2C 抓包 | 抓 MCP23008 初始化和运行时写入 |
| Day 5 | SPI/UART 候选抓包 | 同时抓 Pin 19/21/23/24 与 Pin 8/10 |
| Day 6 | 数据整理 | 做通道映射、协议解码、寄存器差异表 |
| Day 7 | ESP32-S3 只读原型 | 只做 I2C scan 和 MCP23008 dump |

首周结束时应该得到：

- `hardware_notes.md`
- `protocol_notes.md`
- 至少 3 份 `.sal` 或 CSV 抓包文件
- `minerd_events.log`
- MCP23008 三状态寄存器表
- 初步判断：SPI / UART / unknown

### 15.4 决策门：什么时候可以接 ESP32

只有满足以下条件，才建议把 ESP32-S3 接到 HAT：

| 条件 | 必须满足 |
|---|---|
| HAT 主机侧电平 | 已确认是 3.3V 或已加电平转换 |
| GND | 已确认共地 |
| I2C 地址 | 已确认 MCP23008 地址 |
| ESP32 固件 | 默认只读，不写寄存器 |
| 接线 | 每条未知信号串 100Ω-330Ω |
| 电源 | HAT 用原 DC Jack，ESP32 用 USB，不互相供电 |
| 散热 | 原散热器和风扇保持 |

如果任一条件不满足，只允许逻辑分析仪被动抓包，不允许 ESP32 主动连接。

### 15.5 决策门：什么时候可以写 MCP23008

只有满足以下条件，才允许写 MCP23008：

| 条件 | 必须满足 |
|---|---|
| 已有原机 I2C 抓包 | 知道原机写了哪些寄存器 |
| 已有 GP 引脚追线 | 知道被写位连接对象 |
| 已有安全回退方案 | 可恢复 all-input 或原始寄存器值 |
| 已有电流监控 | 写入时能观察异常电流 |
| 只写一个位 | 不批量乱写 |
| 记录日志 | 每次写入保存时间、寄存器、值 |

建议写入流程：

```text
read all regs
save snapshot
write one safe bit
wait 100 ms
read all regs
observe current/fan/LED
restore original value
read all regs
save snapshot
```

### 15.6 决策门：什么时候可以复刻 ASIC 初始化

只有满足以下条件，才进入 ASIC transport 复刻：

- 已确认 transport 是 SPI 或 UART。
- 已确认电压域和方向。
- 已确认 AVCH16T245 `DIR/OE` 状态。
- 已捕获原机初始化 TX/RX。
- 已能复刻 MCP23008 reset/enable。
- 已有风扇和散热。
- 已有可调电源限流。
- 已准备好立即断电。

第一轮复刻只回放初始化，不下发 work：

```text
assert safe reset state
enable transport
replay init bytes
capture response
disable transport
compare with original capture
```

### 15.7 第一批建议实际文件

建议现在就把大文档拆出这些文件，后续更容易维护：

| 文件 | 从本文档提取章节 |
|---|---|
| `README.md` | 13.2、13.13、12.12 |
| `docs/safety_checklist.md` | 11.4、12.11、15.4-15.6 |
| `docs/raspberry_pi_setup.md` | 第九轮、第十一轮 Pi5 部分 |
| `docs/esp32_s3_plan.md` | 8.8、11.3-11.10、12.6 |
| `docs/hardware_notes.md` | 12.2、14.2-14.10 |
| `docs/protocol_notes.md` | 12.3、14.11 |
| `docs/references.md` | 10.2、13.5 |
| `docs/open_questions.md` | 10.7、10.8、11.11 |

### 15.8 当前开放问题清单

这份清单适合放进 `docs/open_questions.md`：

| ID | 问题 | 当前状态 | 解决方法 |
|---|---|---|---|
| Q001 | ASIC 型号是什么 | 未确认 | 拍芯片高清图，查丝印 |
| Q002 | ASIC 主通信是 SPI 还是 UART | 未确认 | 逻辑分析仪抓包 |
| Q003 | MCP23008 地址是否为 `0x20` | 条件推测 | `i2cdetect -y 1` |
| Q004 | GP0-GP7 各控制什么 | 未确认 | 通断追线 + I2C 抓包 |
| Q005 | AVCH16T245 A/B 侧电压是多少 | 未确认 | 万用表测 VCCA/VCCB |
| Q006 | DIR/OE 由谁控制 | 未确认 | 通断追线 + 上电测量 |
| Q007 | 原 `minerd` 在 Pi 5 能否运行 | 未验证 | Pi 5 实测 |
| Q008 | `swirl+tcp` 与标准 Stratum 差异 | 未整理 | 源码分析 + 抓包 |
| Q009 | ASIC core 电压是多少 | 未确认 | 找 buck 输出并测量 |
| Q010 | 风扇是常开还是受控 | 未确认 | 上电观察 + 追线 |

### 15.9 当前最短路径

如果只追求最快跑通 ESP32-S3 控制，应按这条最短路径走：

```text
1. 树莓派确认 MCP23008 地址
2. 抓 minerd 启动时的 MCP23008 I2C 写入
3. 确认 GP reset/enable 位
4. ESP32-S3 复刻 MCP23008 初始化
5. 抓 ASIC 主通信线
6. ESP32-S3 回放 ASIC 初始化
7. 固定 work 测 nonce
8. 接 Stratum
```

如果只追求开源资料可靠，应按这条最短路径走：

```text
1. 拆 README/docs
2. 建 references.md
3. 建 hardware_notes.md
4. 建 protocol_notes.md
5. 上传高清标注图
6. 上传原始命令输出
7. 所有结论加 L0-L5 等级
```

### 15.10 鼓励但不跳步

这个项目真正难的地方不是写代码，而是不要让错误假设滚雪球。只要坚持以下节奏，就能稳：

```text
看到 -> 记录
测到 -> 标注
抓到 -> 解码
确认 -> 复刻
复刻成功 -> 扩展
```

这比“直接接 ESP32 开挖”慢一点，但最后会省非常多返工。

---

## ✅ 第十六轮：当前一定可实现能力边界记录 (2026-06-16 16:45)

### 16.1 本轮记录目的

本轮专门记录当前阶段“已经可以确定实现的能力”和“尚不能保证实现的能力”。这是后续开发的边界条件，避免把推测、计划或硬件可能性误写成已经能驱动 ASIC 挖矿。

### 16.2 当前一定可以实现的内容

| 能力 | 当前状态 | 说明 |
|---|---|---|
| 开源资料整理 | 一定可实现 | 可将现有内容整理为 README、硬件说明、树莓派说明、ESP32 计划、协议记录模板 |
| 树莓派基础总线访问 | 一定可实现 | 树莓派 2/3/4/5 可用于启用和测试 I2C、SPI、UART |
| HAT 信息读取 | 条件可实现 | 若 HAT EEPROM 被系统识别，可读取 `/proc/device-tree/hat/product`、`hat/uuid` |
| MCP23008 I2C 扫描 | 一定可实现 | 可通过 `i2cdetect -y 1` 检查是否存在 I2C 设备 |
| MCP23008 只读寄存器 | 条件可实现 | 若地址确认为 `0x20` 或其他地址，可只读 `IODIR/GPIO/OLAT` 等寄存器 |
| minerd socket 监听 | 条件可实现 | 若原机 `minerd` 正常运行，可监听 `/tmp/minerd.sock` |
| minerd 事件解析 | 一定可实现 | 现有 `monitor_minerd.py` 可解析 `StatisticsEvent`、`ShareSubmitEvent` 等 JSON 事件 |
| 逻辑分析仪被动抓包 | 一定可实现 | 可抓 I2C、SPI 候选线、UART 候选线，不主动驱动硬件 |
| ESP32-S3 只读探测固件 | 一定可实现 | 可实现 I2C scan、MCP23008 probe、register dump、串口日志 |
| ESP32-S3 新主控框架 | 一定可实现 | ESP32-S3 具备 I2C/SPI/UART/Wi-Fi/Web/Stratum client 框架能力 |
| 硬件实测记录体系 | 一定可实现 | 可建立 `hardware_notes.md`、`protocol_notes.md`、抓包模板、可靠性等级 |

### 16.3 当前推荐立即执行的命令

树莓派侧基础检查：

```bash
i2cdetect -y 1
ls /dev/spidev*
ls -l /dev/serial0 /dev/ttyAMA0 /dev/ttyS0
cat /proc/device-tree/hat/product 2>/dev/null
cat /proc/device-tree/hat/uuid 2>/dev/null
```

如果 MCP23008 地址为 `0x20`，只读寄存器：

```bash
i2cget -y 1 0x20 0x00
i2cget -y 1 0x20 0x09
i2cget -y 1 0x20 0x0A
```

如果 `minerd` 已运行，监听状态：

```bash
python monitor_minerd.py
```

### 16.4 当前不能保证实现的内容

| 能力 | 当前状态 | 原因 |
|---|---|---|
| 直接驱动 ASIC 挖矿 | 不能保证 | ASIC transport protocol 未确认 |
| ESP32 直接替代树莓派完整挖矿 | 不能保证 | ASIC 初始化、work 格式、nonce 返回格式未知 |
| 树莓派 5 原样运行旧 `minerd` | 不能保证 | 旧软件/驱动/依赖和 Pi 5 环境兼容性未实测 |
| 直接写 MCP23008 控制位 | 不能保证且不建议 | GP0-GP7 连接对象未确认 |
| 确认主通信是 SPI | 不能保证 | 需要逻辑分析仪抓包 |
| 确认主通信是 UART | 不能保证 | 需要逻辑分析仪抓包 |
| 确认 ASIC 型号 | 不能保证 | 需要高清芯片标记和资料核对 |
| 确认 ASIC core 电压 | 不能保证 | 需要板级测量 |
| 确认 AVCH16T245 A/B 电压域 | 不能保证 | 需要测 VCCA/VCCB 和追线 |
| 确认风扇/电源/复位完整时序 | 不能保证 | 需要抓包和实测 |

### 16.5 当前阶段一句话结论

```text
当前一定能实现：识别、读取、监听、抓包、只读探测、资料开源化、ESP32-S3 控制框架。
当前不能保证：完整 ASIC 挖矿驱动、ESP32 直接替代树莓派、树莓派 5 原样兼容旧 minerd。
```

### 16.6 下一步最小闭环

下一步只追求一个安全闭环：

```text
树莓派 i2cdetect
  -> 读取 MCP23008
  -> 启动 minerd
  -> 监听 /tmp/minerd.sock
  -> 逻辑分析仪抓 I2C/SPI/UART
  -> 写入 hardware_notes.md 和 protocol_notes.md
```

完成这个闭环后，才进入 ESP32-S3 写控制位和 ASIC 初始化复刻。

---

## ✅ 第十七轮：工程包拆分计划与可生成文件清单 (2026-06-16 17:10)

### 17.1 本轮目标

当前 `development_log.md` 已经包含大量资料，适合作为总记录，但不适合长期维护。下一步应把它拆成“开源工程包”，让每类资料有自己的文件。

本轮记录拆分计划，后续可按本节逐个生成文件。

### 17.2 推荐第一批生成的文件

第一批文件应优先服务“安全实测”和“只读验证”。

| 优先级 | 文件 | 类型 | 目的 |
|---|---|---|---|
| P0 | `README.md` | 开源入口 | 告诉别人项目状态、安全边界、当前不能保证挖矿 |
| P0 | `docs/safety_checklist.md` | 安全文档 | 防止误接、误写、误上电 |
| P0 | `docs/hardware_notes.md` | 实测表 | 记录电压、电流、芯片、测试点 |
| P0 | `docs/protocol_notes.md` | 抓包表 | 记录 I2C/SPI/UART 波形和解码 |
| P0 | `docs/raspberry_pi_setup.md` | 树莓派指南 | 树莓派 2/3/4/5 操作步骤 |
| P0 | `docs/esp32_s3_plan.md` | ESP32 计划 | ESP32-S3 只读探测和后续控制路线 |
| P1 | `docs/references.md` | 引用来源 | 官方文档、数据手册、源码位置 |
| P1 | `docs/open_questions.md` | 未解问题 | Q001-Q010 和后续新问题 |
| P1 | `scripts/raspi_collect_info.sh` | 采集脚本 | 一键收集树莓派状态 |
| P1 | `scripts/read_mcp23008.py` | 只读脚本 | 只读 MCP23008 寄存器 |
| P2 | `firmware/esp32_s3_i2c_probe/` | 固件 | ESP32-S3 I2C 只读探测 |
| P2 | `captures/README.md` | 数据说明 | 规范抓包文件命名和提交方式 |

### 17.3 README 最小版本内容

`README.md` 第一版不需要很长，但必须清楚。

建议包含：

```markdown
# 21 Bitcoin Computer HAT Restoration

Independent notes and tools for studying the 21 Bitcoin Computer mining HAT.

## Current Status

This project is currently in the measurement and reverse-engineering phase.

Confirmed:
- Raspberry Pi can be used as a development and measurement host.
- MCP23008 can be scanned/read over I2C if present on the bus.
- `two1` source confirms `/tmp/minerd.sock`, `/run/minerd.pid`, and
  `swirl+tcp://grid.21.co:21006`.
- ESP32-S3 is a suitable candidate for a modern controller prototype.

Not confirmed:
- ASIC transport protocol.
- ASIC model and voltage.
- MCP23008 GP0-GP7 board functions.
- ESP32 direct mining support.
- Raspberry Pi 5 original `minerd` compatibility.

## Safety

Read `docs/safety_checklist.md` before powering or connecting anything.

## Quick Start: Read-only Raspberry Pi Checks

```bash
i2cdetect -y 1
cat /proc/device-tree/hat/product 2>/dev/null
cat /proc/device-tree/hat/uuid 2>/dev/null
```

## Quick Start: Read-only MCP23008

```bash
i2cget -y 1 0x20 0x00
i2cget -y 1 0x20 0x09
i2cget -y 1 0x20 0x0A
```
```

### 17.4 `docs/safety_checklist.md` 最小内容

```markdown
# Safety Checklist

## Before Power

- [ ] Board visually inspected.
- [ ] No obvious burned parts or loose connectors.
- [ ] Fan spins freely.
- [ ] Heatsink is installed.
- [ ] DC input polarity confirmed.
- [ ] 5V/3.3V rails checked for shorts to GND.

## Before Connecting ESP32

- [ ] HAT signal voltage confirmed.
- [ ] ESP32 and HAT share GND.
- [ ] HAT powered from original DC input.
- [ ] ESP32 powered from USB.
- [ ] Unknown lines have 100R-330R series resistors.
- [ ] ESP32 firmware is read-only.

## Never Do

- [ ] Do not connect 5V GPIO to HAT logic.
- [ ] Do not write MCP23008 before GP functions are known.
- [ ] Do not drive unknown MISO/RX-like lines.
- [ ] Do not power ASIC without cooling.
```

### 17.5 `docs/hardware_notes.md` 第一版表单

```markdown
# Hardware Notes

## Board

| Field | Value | Evidence |
|---|---|---|
| Board name | TBD | |
| Board marking | TBD | |
| Revision | TBD | |
| Serial | TBD | |
| Host used | TBD | |

## Chips

| Ref | Marking | Part Guess | Evidence | Reliability |
|---|---|---|---|---|
| U1 | TBD | AVCH16T245 compatible? | photo | L4 |
| U12 | TBD | MCP23008? | photo/datasheet | L4 |
| U15 | TBD | ASIC | photo | L5 |

## Power Measurements

| Rail | Idle | minerd start | mining | Test Point | Notes |
|---|---:|---:|---:|---|---|
| VIN | TBD | TBD | TBD | TBD | |
| 5V | TBD | TBD | TBD | TBD | |
| 3V3 | TBD | TBD | TBD | TBD | |
| ASIC core | TBD | TBD | TBD | TBD | |
| Fan | TBD | TBD | TBD | TBD | |

## MCP23008 Snapshots

| State | IODIR | GPIO | OLAT | Notes |
|---|---|---|---|---|
| power on | TBD | TBD | TBD | |
| before minerd | TBD | TBD | TBD | |
| minerd running | TBD | TBD | TBD | |
```

### 17.6 `docs/protocol_notes.md` 第一版表单

```markdown
# Protocol Notes

## Capture Index

| File | Host | State | Channels | Finding |
|---|---|---|---|---|
| TBD | TBD | power on | TBD | TBD |

## I2C Findings

| Time | Address | Operation | Register | Value | Meaning |
|---|---|---|---|---|---|
| TBD | TBD | TBD | TBD | TBD | TBD |

## SPI Candidate

| Pin | Signal | Activity | Decode | Notes |
|---|---|---|---|---|
| 19 | MOSI? | TBD | TBD | |
| 21 | MISO? | TBD | TBD | |
| 23 | SCLK? | TBD | TBD | |
| 24 | CE0? | TBD | TBD | |

## UART Candidate

| Pin/Test Point | Baud Guess | Decode | Notes |
|---|---:|---|---|
| TBD | TBD | TBD | |
```

### 17.7 脚本优先级

后续写脚本时按这个顺序：

| 顺序 | 脚本 | 风险 | 原因 |
|---|---|---|---|
| 1 | `raspi_collect_info.sh` | 低 | 只读系统信息 |
| 2 | `read_mcp23008.py` | 低 | 只读 I2C 寄存器 |
| 3 | `minerd_event_logger.py` | 低 | 只读 socket |
| 4 | `compare_mcp23008_snapshots.py` | 低 | 离线比较 |
| 5 | ESP32-S3 I2C scan firmware | 低 | 默认只读 |
| 6 | ESP32-S3 MCP23008 write test | 中 | 必须确认 GP 位后再做 |
| 7 | ASIC transport replay | 高 | 必须抓包和确认电压后再做 |

### 17.8 `minerd_event_logger.py` 设计

现有 `monitor_minerd.py` 会打印友好信息。后续可以新增一个“原始日志采集器”，专门保存 JSONL。

目标：

- 连接 `/tmp/minerd.sock`。
- 每收到一行 JSON，原样保存一行。
- 不解释、不改写、不丢字段。
- 文件名带时间戳。

输出示例：

```text
20260616_21hat_minerd_events.jsonl
```

每行：

```json
{"type":"StatisticsEvent","payload":{...}}
```

这个文件后续可用于写 parser、画图、对齐逻辑分析仪时间。

### 17.9 ESP32-S3 固件目录草案

```text
firmware/esp32_s3_i2c_probe/
  README.md
  CMakeLists.txt
  sdkconfig.defaults
  main/
    CMakeLists.txt
    app_main.c
    board_config.h
    i2c_scan.c
    i2c_scan.h
    mcp23008.c
    mcp23008.h
```

`board_config.h` 第一版只需要：

```c
#pragma once

#define I2C_PORT_NUM 0
#define I2C_SDA_GPIO 8
#define I2C_SCL_GPIO 9
#define I2C_FREQ_HZ 100000

#define MCP23008_ADDR_START 0x20
#define MCP23008_ADDR_END   0x27

#define ENABLE_MCP23008_WRITE 0
```

注意：GPIO 8/9 只是 ESP32-S3 DevKit 上的建议示例，最终以实际开发板引脚和接线为准。

### 17.10 数据提交格式

开源后别人提交数据时，要求至少包含：

```text
hardware:
  board_revision:
  host:
  power_supply:
  notes:

measurement:
  date:
  tool:
  sample_rate:
  voltage_threshold:
  channels:

files:
  raw_capture:
  decoded_csv:
  photos:
  logs:
```

可以放进 `captures/README.md`，减少无效数据。

### 17.11 后续自动化检查

等拆分成仓库后，可以加简单检查：

- Markdown 链接检查。
- 文件命名检查。
- 确认抓包文件有对应 metadata。
- 确认危险脚本默认只读。
- 确认 ESP32 固件默认 `ENABLE_MCP23008_WRITE=0`。

### 17.12 本轮结论

下一步最有价值的不是继续把大日志堆厚，而是开始拆文件：

```text
README.md
docs/safety_checklist.md
docs/hardware_notes.md
docs/protocol_notes.md
scripts/raspi_collect_info.sh
scripts/read_mcp23008.py
```

这些文件生成后，项目就从“资料记录”变成了“可执行工程包”。

---

## ✅ 第十八轮：知识产权边界与外部项目引用方式 (2026-06-16 17:30)

### 18.1 本轮记录目的

本项目后续计划开源，因此必须明确知识产权边界。原则是：

```text
不复制别人的源码
不搬运别人的文档
不把别人的协议/图片/设计当成自己的成果
只做简短说明、用途解释和原始链接引用
```

也就是说，遇到 Bitaxe、ESP-Miner、Raspberry Pi、Espressif、Microchip、TI 等外部资料时，应写“它能作为哪一类参考”，然后用链接跳转到原始来源。

### 18.2 推荐引用格式

建议统一使用以下格式：

```markdown
说明文字。  
↗ 来源：<URL>
```

或者表格格式：

```markdown
| 项目 | 可参考内容 | 链接 |
|---|---|---|
| ESP-Miner | ESP32 矿机固件架构、Web API、构建流程 | ↗ https://github.com/bitaxeorg/ESP-Miner |
```

符号建议：

| 符号 | 用途 |
|---|---|
| `↗` | 外部链接 / 原始来源 |
| `参考` | 只作思路参考，不代表可直接复用 |
| `官方` | 厂商或项目官方资料 |
| `待验证` | 本项目尚未实测确认 |

### 18.3 外部项目引用清单

以下项目只能作为外部参考，不应直接复制代码或文档到本项目中。

| 项目/资料 | 说明 | 链接 |
|---|---|---|
| ESP-Miner | 开源 ESP32 比特币 ASIC 矿机固件，可参考固件结构、Web API、配置方式、构建流程；不能直接假设兼容 21 ASIC | ↗ https://github.com/bitaxeorg/ESP-Miner |
| Bitaxe hardware | 开源 ESP32 + ASIC 矿机硬件，可参考电源、风扇、主控、ASIC 板级架构；不能直接套用到 21 HAT | ↗ https://github.com/bitaxeorg/bitaxe |
| Raspberry Pi 官方文档 | 树莓派 40-pin、I2C、SPI、UART、GPIO 电平和系统配置参考 | ↗ https://www.raspberrypi.com/documentation/computers/raspberry-pi.html |
| Raspberry Pi 配置文档 | `config.txt`、`dtparam`、串口/I2C/SPI 启用方式参考 | ↗ https://www.raspberrypi.com/documentation/computers/configuration.html |
| Espressif ESP32-S3 Datasheet | ESP32-S3 外设能力、GPIO、I2C、SPI、UART、Wi-Fi 能力参考 | ↗ https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf |
| Microchip MCP23008 Datasheet | MCP23008 寄存器、I2C 地址、引脚功能、GP7 限制等一手资料 | ↗ https://ww1.microchip.com/downloads/aemDocuments/documents/APID/ProductDocuments/DataSheets/MCP23008-and-MCP23008-Data-Sheet-DS20001919.pdf |
| TI SN74AVCH16T245 Datasheet | AVCH16T245 类双电源总线收发器的 `DIR/OE`、电压域和高阻行为参考 | ↗ https://www.ti.com/lit/ds/symlink/sn74avch16t245.pdf |

### 18.4 README 中建议加入的知识产权说明

后续 `README.md` 建议加入：

```markdown
## Intellectual Property and Attribution

This project does not claim ownership of external projects, datasheets,
vendor documentation, or third-party source code. External resources are
referenced by short descriptions and links to their original locations.

Bitaxe, ESP-Miner, Raspberry Pi, Espressif, Microchip, TI, and other named
projects or vendors remain the property of their respective owners.

Where third-party projects are mentioned, they are used only as engineering
references. Their code, documentation, schematics, and licenses should be
consulted at the original source before reuse.
```

中文版本：

```markdown
## 知识产权与引用说明

本项目不主张拥有外部项目、数据手册、厂商文档或第三方源码的权利。
所有外部资料仅用简短说明和原始链接进行引用。

Bitaxe、ESP-Miner、Raspberry Pi、Espressif、Microchip、TI 等名称及项目
归其各自权利人所有。

本文档提到的第三方项目仅作为工程参考。若需要复用其代码、文档、原理图
或固件，请前往原始仓库或官方页面查看对应许可证。
```

### 18.5 本项目应避免的做法

| 不建议做法 | 原因 |
|---|---|
| 复制 ESP-Miner 源码到本仓库 | 可能引入许可证义务和维护责任 |
| 复制 Bitaxe 原理图/PCB 文件 | 容易造成版权和许可证混淆 |
| 把数据手册 PDF 直接放进仓库 | 厂商文档通常有再分发限制 |
| 使用网络图片作为本项目硬件图 | 图片版权不清楚 |
| 把第三方协议说明改写成“本项目原创发现” | 不尊重原作者，也会损害开源可信度 |
| 未注明来源引用技术结论 | 后续难以核验 |

### 18.6 推荐做法

| 推荐做法 | 说明 |
|---|---|
| 写自己的解释 | 用自己的语言说明“为什么参考它” |
| 放原始链接 | 用 `↗` 指向原仓库或官方文档 |
| 标注许可证 | 如果引用项目有 LICENSE，提醒读者查看 |
| 不复制大段内容 | 只摘取必要事实，避免搬运 |
| 自己画图 | 基于实测重新绘制框图/流程图 |
| 自己采集照片和波形 | 形成属于本项目的实测资料 |
| 明确“参考，不兼容” | 尤其是 Bitaxe/ESP-Miner，不能误导读者以为能直接用于 21 ASIC |

### 18.7 对 Bitaxe / ESP-Miner 的推荐写法

建议在文档中这样写：

```markdown
ESP-Miner 是一个开源 ESP32 比特币 ASIC 矿机固件项目，可作为
“ESP32 + ASIC + Web UI + 矿池连接”的软件架构参考。但 21 Bitcoin
Computer 的 ASIC 型号和通信协议尚未确认，因此 ESP-Miner 不能直接用于
驱动本项目硬件。

↗ 参考： https://github.com/bitaxeorg/ESP-Miner
```

```markdown
Bitaxe 是开源比特币 ASIC 矿机硬件项目，可作为电源、散热、ESP32 主控
和现代开源矿机结构参考。但本项目的 HAT、电平转换、ASIC 协议和供电拓扑
需要独立实测，不能直接套用 Bitaxe 设计。

↗ 参考： https://github.com/bitaxeorg/bitaxe
```

---

## ✅ 第十九轮：外网协议资料检索结论与后续追踪方向 (2026-06-16 18:05)

### 19.1 本轮检索目标

本轮继续尝试寻找 21 Bitcoin Computer 的公开协议资料，重点搜索：

- 21 Bitcoin Computer ASIC protocol
- 21BC1 ASIC protocol
- 21 Bitcoin Computer minerd protocol
- `swirl+tcp://grid.21.co:21006`
- `/tmp/minerd.sock`
- `StatisticsEvent`
- `ShareSubmitEvent`
- 21 Bitcoin Computer teardown / HAT / MCP23008 / SPI / UART

### 19.2 检索结论

当前外网检索结论：

```text
没有找到 21 Bitcoin Computer ASIC 私有通信协议的公开文档。
没有找到可直接说明 21 HAT 与 ASIC 之间 SPI/UART 数据包格式的资料。
没有找到可直接复用的 21BC1 初始化序列、work 格式、nonce 返回格式。
```

因此，当前仍应维持原判断：

```text
21 ASIC transport protocol = UNKNOWN
必须通过原机抓包逆向。
```

### 19.3 本轮找到的可参考资料

| 资料 | 能参考什么 | 不能当成什么 | 链接 |
|---|---|---|---|
| ESP-Miner | ESP32 矿机固件结构、Web API、构建方式、现代开源 ASIC 控制项目组织方式 | 不能当成 21 ASIC 协议 | ↗ https://github.com/bitaxeorg/ESP-Miner |
| Bitaxe hardware | ESP32 + ASIC + 电源 + 散热 + Web 管理的现代开源矿机硬件参考 | 不能直接套用到 21 HAT | ↗ https://github.com/bitaxeorg/bitaxe |
| Stratum mining protocol 相关论文 | Stratum 是矿池通信层，负责获取 job、提交 share | 不是 HAT 到 ASIC 的硬件协议 | ↗ https://arxiv.org/abs/1703.06545 |
| Bitcoin mining protocol/挖矿基础资料 | 解释 double SHA-256、nonce、target、share、矿池角色 | 不能提供 21 ASIC 私有包格式 | ↗ https://en.wikipedia.org/wiki/Bitcoin_protocol |
| 21.co 公司转型报道 | 说明 21 Co. 曾从挖矿软硬件转向微支付/邮件产品 | 不能提供硬件协议 | ↗ https://www.axios.com/2017/12/15/bitcoin-startup-seeks-to-solve-common-problems-1513300378 |

### 19.4 为什么网上难找到这个协议

推测原因：

- 21 Bitcoin Computer 是商业产品，ASIC/HAT 协议未必公开。
- `two1` 开源部分主要是钱包、微支付、命令行和服务端/客户端逻辑，不一定包含底层矿片驱动源码。
- 真正控制 ASIC 的 `minerd` 可能是二进制程序或系统组件，不在当前 Python 源码包中。
- 该产品时间较早、生命周期较短，公开拆解和逆向资料很少。
- 21 公司后来业务方向转向微支付/通信/其他产品，原硬件资料可能散失或下线。

### 19.5 当前协议资料分层

| 层级 | 当前资料状态 | 处理方式 |
|---|---|---|
| Bitcoin 挖矿算法 | 公开、资料充分 | 可直接实现 double SHA-256、nonce、target/share 验证 |
| 现代 Stratum 矿池协议 | 公开资料较多 | 可作为 ESP32 后续联网挖矿层 |
| two1 `swirl+tcp` | 本地源码只确认 URL，细节未完整整理 | 继续查源码和抓网络包 |
| `minerd.sock` JSON 事件 | 本地源码可确认 socket 和 StatisticsEvent | 可写 logger 和 parser |
| MCP23008 I2C 控制 | 数据手册明确 | 可写只读/解码工具 |
| 21 HAT ASIC transport | 未找到公开资料 | 必须逻辑分析仪抓包 |

### 19.6 可立即开发的解码器类型

虽然没找到 ASIC 私有协议，仍可先开发以下解码器：

| 解码器 | 当前能否开发 | 输入 | 输出 |
|---|---|---|---|
| `decode_minerd_events.py` | 可以 | `/tmp/minerd.sock` JSONL | 事件时间线、算力、share |
| `decode_i2c_mcp23008.py` | 可以 | I2C CSV / 手工寄存器记录 | MCP23008 寄存器含义 |
| `decode_spi_transactions.py` | 可以做框架 | SPI CSV | 按 CS 分组的原始事务 |
| `decode_uart_frames.py` | 可以做框架 | UART CSV/hex | 按时间输出原始帧 |
| `sha256_mining_test.py` | 可以 | block header / nonce | double SHA-256、target 判断 |
| `asic_protocol_decoder.py` | 暂不能完整开发 | 需要真实 SPI/UART 抓包 | 目前只能输出 unknown frame |

### 19.7 ASIC 协议后续搜索关键词

后续继续联网检索时，可用以下关键词：

```text
"21 Bitcoin Computer" "ASIC"
"21 Bitcoin Computer" "minerd"
"21 Bitcoin Computer" "teardown"
"21 Bitcoin Computer" "HAT"
"21BC1" "ASIC"
"21BC1" "minerd"
"21 Inc" "Bitcoin Computer" "hardware"
"swirl+tcp" "grid.21.co"
"TWO1_POOL_URL" "swirl"
"/tmp/minerd.sock" "StatisticsEvent"
"ShareSubmitEvent" "minerd"
"21 Bitcoin" "MCP23008"
"21 Bitcoin" "AVCH16T245"
"830-0016" "21 Inc"
```

### 19.8 下一步最有效方法：抓包优先于继续搜索

本轮检索说明：公开网页上很可能没有现成协议。因此下一步最高价值工作仍是实测：

```text
1. 原机启动 minerd
2. 逻辑分析仪抓 I2C/SPI/UART
3. 保存原始波形
4. 解码 MCP23008
5. 判断 ASIC transport
6. 做 replay
```

继续搜索也有价值，但不应阻塞实测。建议二者并行：

| 方向 | 目标 |
|---|---|
| 搜索 | 找历史资料、论坛、FCC、拆解、旧 GitHub 镜像 |
| 实测 | 获得本板真实协议，建立自己的开源资料 |

### 19.9 对文档的更新原则

因为未找到公开协议，开源文档中不能写：

```text
21 ASIC 使用 SPI 协议
21 ASIC 使用 UART 协议
21 ASIC 兼容 Bitaxe/BM1366
ESP-Miner 可直接驱动 21 HAT
```

只能写：

```text
SPI/UART 均为候选，需要抓包确认。
Bitaxe/ESP-Miner 仅作 ESP32+ASIC 架构参考。
21 ASIC 私有协议暂无公开资料，当前必须实测逆向。
```

### 19.10 本轮结论

```text
外网检索没有找到 21 Bitcoin Computer ASIC 私有协议。
当前能依赖的资料是：本地 two1 源码、公开数据手册、Raspberry Pi/Espressif 官方资料、Bitaxe/ESP-Miner 架构参考。
真正的 21 HAT ASIC 协议必须通过原机抓包建立。
```

---

## ✅ 第二十轮：本地源码中的 Swirl/Work 协议结构补充 (2026-06-16 18:35)

### 20.1 本轮发现

虽然外网没有找到 21 ASIC 私有通信协议，但本地 `two1` 源码中保留了 `swirl.proto` 生成后的 protobuf 文件：

```text
two1_source/two1-3.10.9/two1/server/swirl_pb3.py
```

以及消息封装代码：

```text
two1_source/two1-3.10.9/two1/server/message_factory.py
```

这说明至少可以确认 **two1 矿池/主控软件之间的 Swirl work/share 消息结构**。这不是 HAT 到 ASIC 的私有协议，但它能告诉我们：

- `minerd` 或 CPU mining 需要什么 work 字段。
- share 提交需要哪些字段。
- 后续写 Stratum/Swirl 转换器时需要哪些中间数据。
- 后续写 SHA-256/nonce 测试工具时需要哪些输入。

### 20.2 Swirl 消息外层封装

`message_factory.py` 中 `_encode_object()` 显示 Swirl protobuf 消息前面有 2 字节大端长度头：

```python
msg_str = obj.SerializeToString()
header = struct.pack('>H', len(msg_str))
return header + msg_str
```

读取时也是：

```python
head_buffer = content[0:2]
pkt = content[2:]
client_message.ParseFromString(pkt)
```

因此 Swirl 消息外层格式可记录为：

```text
uint16_be length
protobuf payload
```

注意：`mine.py` 中 REST 获取 work 时还会先对 `response.content` 做 base64 decode，再交给 `SwirlMessageFactory.read_object()`。

### 20.3 SwirlClientMessage 结构

根据 `swirl_pb3.py`，客户端消息主要有两个 oneof：

```text
SwirlClientMessage
  auth_request
  submit_share_request
```

#### AuthRequest

| 字段 | 类型 | 说明 |
|---|---|---|
| `hardware` | enum | `bitshare` 或 `generic` |
| `username` | string | 21 用户名 |
| `uuid` | string | 设备 UUID |

`message_factory.py` 中 `create_auth_request(username, uuid)` 会设置：

```text
hardware = generic
username = username
uuid = uuid
```

#### SubmitShareRequest

| 字段 | 类型 | 说明 |
|---|---|---|
| `message_id` | uint32 | 客户端随机消息 ID |
| `work_id` | uint32 | work 标识 |
| `enonce2` | bytes | extra nonce 2 |
| `otime` | uint32 | 提交时间 |
| `nonce` | uint32 | 找到的 nonce |

`mine.py` 中 `save_work()` 使用：

```python
create_submit_share_request(
    message_id=message_id,
    work_id=share.work_id,
    enonce2=share.enonce2,
    otime=share.otime,
    nonce=share.nonce
)
```

### 20.4 SwirlServerMessage 结构

服务端消息主要有三个 oneof：

```text
SwirlServerMessage
  auth_reply
  submit_share_reply
  work_notification
```

#### AuthReply

AuthReply 有三类：

| 类型 | 说明 |
|---|---|
| `auth_reply_yes` | 认证成功 |
| `auth_reply_no` | 认证失败 |
| `auth_reply_pool_down` | 矿池不可用 |

`auth_reply_yes` 字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `enonce1` | bytes | extra nonce 1 |
| `enonce2_size` | uint32 | extra nonce 2 字节长度 |
| `wallet_id` | uint32 | 钱包 ID |

#### SubmitShareReply

| 字段 | 类型 | 说明 |
|---|---|---|
| `message_id` | uint32 | 对应提交消息 ID |
| `submit_status` | enum | `good` / `bad` / `stale` / `duplicate` |

#### WorkNotification

这是最关键的 work 结构。

| 字段 | 类型 | 说明 |
|---|---|---|
| `work_id` | uint32 | work 标识 |
| `version` | uint32 | 区块版本 |
| `prev_block_hash` | bytes | 前一区块 hash |
| `height` | uint32 | 区块高度 |
| `nbits` | uint32 | 区块难度 compact bits |
| `ntime` | uint32 | 时间戳 |
| `coinb1` | bytes | coinbase 前半部分 |
| `coinb2` | bytes | coinbase 后半部分 |
| `merkle_edge` | repeated bytes | merkle 分支 |
| `new_block` | bool | 是否为新块 |
| `bits_pool` | uint32 | pool/share 难度 bits |

### 20.5 CPU mining 逻辑说明

`two1/commands/mine.py` 中 `mine_work()` 展示了如何用 Swirl work 计算 share：

1. 从 `bits_pool` 计算 pool target：

```python
pool_target = utils.bits_to_target(work_msg.bits_pool)
```

2. 遍历 `enonce2`：

```python
for enonce2_num in range(0, 2 ** (enonce2_size * 8)):
    enonce2 = enonce2_num.to_bytes(enonce2_size, byteorder="big")
```

3. 拼 coinbase transaction：

```python
work_msg.coinb1 + enonce1 + enonce2 + work_msg.coinb2
```

4. 构造 CompactBlock：

```python
CompactBlock(
    work_msg.height,
    work_msg.version,
    Hash(work_msg.prev_block_hash),
    work_msg.ntime,
    work_msg.nbits,
    work_msg.merkle_edge,
    cb_txn
)
```

5. 遍历 nonce：

```python
for nonce in range(0xffffffff):
    cb.block_header.nonce = nonce
    h = cb.block_header.hash.to_int('little')
    if h < pool_target:
        return Share(enonce2, nonce, otime, work_id)
```

### 20.6 这对 ASIC 协议逆向有什么帮助

这些源码信息不能直接告诉我们 ASIC SPI/UART 包格式，但能告诉我们 ASIC 最终需要计算的工作内容来自哪里。

也就是说，未来如果抓到 ASIC work 包，可以尝试和 Swirl/CompactBlock 数据对应：

| Swirl/CPU mining 字段 | ASIC 包中可能对应 |
|---|---|
| `version` | block header version |
| `prev_block_hash` | previous block hash |
| `ntime` | block header timestamp |
| `nbits` | block difficulty bits |
| `coinb1/enonce1/enonce2/coinb2` | coinbase / merkle root 来源 |
| `merkle_edge` | merkle root 计算 |
| `bits_pool` | share target |
| `nonce` | ASIC 返回结果 |

ASIC 包可能不直接发送完整 coinbase，而是发送以下某种压缩形式：

```text
midstate
merkle root
ntime
nbits
nonce range
target
job id
```

但具体格式仍必须靠抓包确认。

### 20.7 可立即开发的新工具

基于本轮源码发现，可以新增两个工具：

| 工具 | 当前可行性 | 作用 |
|---|---|---|
| `decode_swirl_message.py` | 可以开发 | 解析 Swirl protobuf 消息，输出 auth/work/share 字段 |
| `swirl_work_to_header.py` | 可以开发 | 根据 WorkNotification + enonce1/enonce2 构造 block header 并验证 nonce |

输入可以是：

```text
base64 work response
二进制 Swirl message
手工 JSON 化后的 WorkNotification
```

输出：

```text
work_id
version
prev_block_hash
ntime
nbits
coinbase tx
merkle root
block header
target
nonce test result
```

### 20.8 与 Stratum 的关系

Swirl 的 WorkNotification 和现代 Stratum 的 `mining.notify` 类似，都提供构造 block header 所需的数据。

可以粗略对应：

| Swirl | Stratum v1 类似字段 |
|---|---|
| `work_id` | job_id |
| `prev_block_hash` | prevhash |
| `coinb1` | coinb1 |
| `coinb2` | coinb2 |
| `merkle_edge` | merkle_branch |
| `version` | version |
| `nbits` | nbits |
| `ntime` | ntime |
| `enonce1` | extranonce1 |
| `enonce2_size` | extranonce2_size |
| `nonce` | nonce |

这说明：如果未来 ASIC transport 跑通，理论上可以做：

```text
Stratum mining.notify
  -> 转成类似 WorkNotification 的内部结构
  -> 生成 ASIC work
  -> ASIC 返回 nonce
  -> mining.submit
```

### 20.9 当前协议分层的更新结论

现在协议分层应更新为：

| 层 | 状态 | 当前掌握程度 |
|---|---|---|
| Bitcoin double SHA-256 | 公开 | 可实现 |
| Stratum v1 | 公开 | 可参考 |
| Swirl work/share protobuf | 本地源码可确认 | 可解析、可写工具 |
| CPU mining work 构造 | 本地源码可确认 | 可复现 |
| `minerd.sock` JSON 事件 | 本地源码部分确认 | 可监听、可记录 |
| MCP23008 I2C 控制 | 数据手册可确认 | 可读、可解码 |
| ASIC SPI/UART 私有协议 | 未公开、未抓包 | 仍未知 |

### 20.10 本轮结论

```text
虽然没有找到 21 ASIC 私有协议，但 two1 源码已经足够补全 Swirl work/share 层。
这意味着我们可以先开发 Swirl 解码器、work 构造器、SHA-256 nonce 验证工具。
真正缺失的仍是 HAT 到 ASIC 的 transport 包格式，需要原机逻辑分析仪抓包。
```

---

## 第二十一轮资料补充：Bitshare、Coinbase padding 与 midstate 线索（2026-06-16 19:00）

本轮继续查找公开资料，并回到本地 `two1` 源码核对。结论是：网上仍没有找到 21 ASIC 私有 SPI/UART 协议的公开说明，但源码里已经出现了足够重要的“工作数据结构线索”，可以指导后续解码器和抓包分析。

### 21.1 网上继续搜索结果

检索关键词包括：

```text
"bitshare" "21 Bitcoin"
"bitshare" "two1" "sha256"
"required_padding_for_bitshare"
"21 Bitshare" ASIC
"sha256_midstate" "21 Bitcoin Computer"
"SwirlServerMessage" "WorkNotification"
```

目前没有找到可确认的 21 Bitshare ASIC transport 协议文档，也没有找到第三方完整复现 21 HAT 到 ASIC 的私有通信包格式。

> 开源记录建议：可以写“未发现公开协议文档”，不要写“协议不存在”。更准确的表述是：截至本轮检索，没有找到可公开引用、可验证的 21 ASIC 私有传输协议资料。

### 21.2 本地源码确认：Bitshare 是 21 芯片相关名称

在 `two1_source/two1-3.10.9/two1/bitcoin/coinbase.py` 中确认存在：

```text
BitshareCoinbaseTransaction
CoinbaseTransactionBuilder.required_padding_for_bitshare()
CoinbaseTransactionBuilder.build_work_parts(bitshare=True)
```

源码注释明确说明这些逻辑是给 `21 Bitshare devices/chips/hasher` 使用的。因此后续文档中可以把这块模块暂称为：

```text
21 Bitshare SHA-256 mining device
```

但仍不应把它等同于某个已知公开 ASIC 型号，除非后续从丝印、显微照片或原厂资料中确认。

### 21.3 Coinbase padding 机制（源码确认）

`required_padding_for_bitshare()` 的目的不是加密，也不是私有认证，而是为了让 coinbase 交易的某一段长度对齐到 SHA-256 的 512-bit 分组边界。

源码逻辑可概括为：

```text
1. 用占位 enonce1 = 0xee * enonce1_len
2. 用占位 enonce2 = 0xdd * enonce2_len
3. 构造 coinbase transaction
4. 去掉最后一个 Bitshare output 和 locktime
5. 计算剩余部分长度是否为 512 bit 的整数倍
6. 不足则在 coinbase input script 末尾补 padding
```

padding 规则：

```text
cb1_len_bits = len(client_serialize()) * 8
num_bits_padding = (512 - (cb1_len_bits % 512)) % 512
num_bytes_padding = num_bits_padding / 8

如果 num_bytes_padding == 0:
    padding = 空
如果 num_bytes_padding == 1:
    padding = 00
如果 num_bytes_padding > 1:
    padding = 第一个字节为 num_bytes_padding - 1
              后面补 num_bytes_padding - 1 个 00
```

这说明 21 Bitshare 芯片很可能需要主控提前准备 coinbase 的 SHA-256 中间状态，或者至少要求 coinbase 的某一部分刚好落在 SHA-256 block 边界上，方便硬件从固定状态继续计算。

### 21.4 CompactBlock 与 midstate（源码确认）

在 `two1_source/two1-3.10.9/two1/bitcoin/block.py` 中确认：

```text
CompactBlock = 为挖矿保存最小状态的区块对象
```

它保存：

```text
BlockHeader
merkle_edge
coinbase_transaction
midstate
```

核心流程：

```text
1. 设置 coinbase_transaction
2. 从 coinbase hash 开始
3. 依次和 merkle_edge 中的 hash 做 double SHA-256
4. 得到 merkle_root
5. 写入 block_header.merkle_root_hash
6. 对 block header 的前 64 字节计算 SHA-256 midstate
```

源码中的关键关系：

```text
cur_hash = coinbase_tx.hash
for e in merkle_edge:
    cur_hash = double_sha256(cur_hash + e)
block_header.merkle_root_hash = cur_hash

midstate = sha256(bytes(block_header)[0:64]).state
```

这进一步证明：21 的挖矿工作流不是“给芯片一整块完整区块让它自己理解 Bitcoin”，而是主控先把 Swirl/Bitcoin work 转成更接近 SHA-256 ASIC 需要的紧凑工作数据。

### 21.5 目前可以推测的 ASIC work 内容（仍需抓包验证）

根据 `CoinbaseTransactionBuilder`、`CompactBlock` 和 `mine_work()` 的关系，ASIC work 包很可能包含以下一种或多种字段：

| 字段 | 依据 | 状态 |
|---|---|---|
| job/work id | Swirl 有 `work_id`，ASIC 返回 nonce 时需要关联任务 | 高概率 |
| block header version | `BlockHeader` 字段 | 高概率 |
| previous block hash | `BlockHeader` 字段 | 高概率 |
| merkle root 或其相关中间值 | `CompactBlock` 会生成 merkle root | 高概率 |
| ntime | `BlockHeader` 字段，share 提交也带 `otime` | 高概率 |
| nbits | `BlockHeader` 字段 | 高概率 |
| nonce 起点/范围 | ASIC 需要枚举 nonce | 高概率 |
| target / pool target | 主控或 ASIC 需要判断 share 是否达标 | 中高概率 |
| SHA-256 midstate | 源码专门计算 header 前 64 字节 midstate | 高概率 |
| coinbase midstate | Bitshare padding 注释直接提到 coinbase midstate | 中高概率 |
| enonce2 | CPU miner 中主控枚举；ASIC 是否枚举未知 | 未确认 |

注意：以上不是协议格式，只是“抓包时要寻找的字段候选”。

### 21.6 对解码器开发的意义

凭目前资料，可以先开发四类工具：

| 工具 | 能否现在做 | 作用 |
|---|---|---|
| `decode_swirl_message.py` | 可以 | 解码 Swirl protobuf work/share 消息 |
| `bitshare_padding_calc.py` | 可以 | 根据 coinbase 参数复现 21 Bitshare padding |
| `compact_block_builder.py` | 可以 | 从 work 字段生成 coinbase、merkle root、block header |
| `asic_trace_correlator.py` | 可以做初版 | 把抓到的 SPI/UART 字节流和已知 work 字段做模式匹配 |

`asic_trace_correlator.py` 的第一版不需要知道完整协议，只需要做“已知字段扫描”：

```text
输入：
  1. Swirl WorkNotification
  2. enonce1 / enonce2 / nonce 测试值
  3. 抓包得到的原始 SPI/UART 字节流

输出：
  1. 哪些字段在抓包中出现
  2. 出现偏移
  3. 大端/小端形式
  4. 是否出现 midstate 8 个 uint32
  5. 是否出现 header tail / ntime / nbits / nonce
```

### 21.7 抓包时优先寻找的字节模式

后续只要能从原装树莓派或原始运行环境里抓到 HAT 通信，就应该优先匹配：

```text
block version: 4 bytes，小端概率高
prev_block_hash: 32 bytes，注意内部字节序
merkle_root: 32 bytes，注意内部字节序
ntime: 4 bytes
nbits: 4 bytes
nonce: 4 bytes
midstate: 8 * uint32，可能大端或小端 word
work_id/job_id: 可能是整数或短字节串
```

如果直接找不到 `coinb1/coinb2`，不代表协议不是它，因为 ASIC 层很可能只接收 merkle root、midstate 或 header tail，而不是完整 coinbase。

### 21.8 对“能不能做解码器/加密算法”的更新结论

更准确地说：

```text
可以做解码器：
  Swirl 层可以完整解码。
  Bitcoin work 构造层可以复现。
  Bitshare padding 可以复现。
  ASIC 抓包关联解码器可以先做字段匹配版。

不建议称为加密算法：
  这里核心是 Bitcoin double SHA-256、coinbase 构造、merkle root、midstate 和 nonce 搜索。
  它不是加密通信协议，也不是可逆加密。
  如果存在私有校验、CRC、帧头、握手或寄存器命令，那属于 ASIC transport 协议，需要抓包确认。
```

### 21.9 外部链接记录（只引用，不搬运）

以下链接可作为开源文档中的参考入口。文档中应只写解释和引用，不复制对方代码或大段原文。

```text
Bitcoin block headers / hash byte order:
↗ https://developer.bitcoin.org/reference/block_chain.html

Raspberry Pi GPIO / SPI / I2C:
↗ https://www.raspberrypi.com/documentation/computers/raspberry-pi.html

ESP32-S3 datasheet:
↗ https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf

Microchip MCP23008 datasheet:
↗ https://ww1.microchip.com/downloads/aemDocuments/documents/APID/ProductDocuments/DataSheets/MCP23008-MCP23S08-Data-Sheet-20001919F.pdf

TI SN74AVCH16T245 datasheet:
↗ https://www.ti.com/lit/ds/symlink/sn74avch16t245.pdf

Bitaxe project:
↗ https://github.com/bitaxeorg/bitaxe

ESP-Miner project:
↗ https://github.com/bitaxeorg/ESP-Miner
```

### 21.10 本轮结论

```text
本轮最大进展不是找到公开 ASIC 私有协议，而是确认了 21 源码中 Bitshare 工作构造的关键路径：

Swirl WorkNotification
  -> coinb1/enonce1/enonce2/coinb2
  -> Bitshare coinbase padding
  -> coinbase hash
  -> merkle root
  -> block header
  -> header midstate
  -> ASIC nonce 搜索

所以后续开发可以分两条线并行：
1. 先实现 Swirl/Bitshare/CompactBlock 的纯软件复现工具。
2. 等有真实 HAT 通信抓包后，用这些已知字段反推 ASIC transport 帧格式。
```

---

## 第二十二轮资料补充：minerd 边界、设备识别与后续抓包路径（2026-06-16 19:20）

本轮继续检查 `two1` 本地源码，重点确认 Python 层、`minerd` 守护进程、HAT 硬件之间的职责边界。

### 22.1 Python 源码里没有真正的 ASIC 底层驱动

通过全文搜索：

```text
Bitshare
midstate
minerd
ASIC
hasher
SPI
UART
nonce
```

目前在 `two1_source/two1-3.10.9` 的 Python 包中，没有发现直接操作 SPI/UART/I2C 去驱动 ASIC 的代码。

确认存在的是：

```text
two1/commands/mine.py
two1/commands/util/bitcoin_computer.py
two1/bitcoin/block.py
two1/bitcoin/coinbase.py
two1/server/message_factory.py
two1/server/swirl_pb3.py
```

这说明 Python 层主要负责：

```text
1. 判断是否是 21 Bitcoin Computer HAT
2. 启动外部 minerd 守护进程
3. 读取 minerd 的 unix socket 状态事件
4. 和 21 后端交换 Swirl work/share
5. 在没有走硬件时，提供 CPU fallback mining 逻辑
```

真正的 HAT -> ASIC 驱动逻辑，大概率在系统里的 `minerd` 二进制程序或其依赖库中，而不在当前 Python 源码包里。

### 22.2 设备识别方式（源码确认）

`two1/commands/util/bitcoin_computer.py` 通过 Linux device tree 判断是否存在 21 HAT：

```text
/proc/device-tree/hat/product
/proc/device-tree/hat/uuid
```

确认逻辑：

```text
has_mining_chip():
    读取 /proc/device-tree/hat/product
    如果内容以 "21 Bitcoin" 开头，则认为有 mining chip

get_device_uuid():
    读取 /proc/device-tree/hat/uuid
```

这对树莓派 5 的意义：

```text
如果树莓派 5 能正确读取 HAT EEPROM / device tree，并且 product 字段仍暴露为 21 Bitcoin 开头，
那么 two1 的 Python 层“识别 HAT”这一步有机会通过。

但这不等于 ASIC 一定能工作，因为真正驱动还依赖 minerd、内核接口、GPIO/SPI/UART/I2C 权限、时序和供电。
```

### 22.3 minerd 启动方式（源码确认）

`two1/commands/mine.py` 中的硬件挖矿路径：

```text
如果 has_mining_chip() 为真：
    如果 /tmp/minerd.sock 连接失败：
        sudo minerd -u <username> <pool_url>
    如果 minerd 已经运行且用户请求 dashboard：
        启动 minertop
    如果 minerd 已经运行但没有 dashboard：
        进入 CPU mining / buffered mining 路径
```

也就是说：

```text
21 mine
  -> 检查 HAT
  -> 启动 sudo minerd
  -> minerd 自己负责和芯片通信
```

当前 Python 源码没有直接告诉我们 `minerd` 内部发给 ASIC 的包格式。

### 22.4 minerd socket 事件（源码确认）

`bitcoin_computer.get_hashrate()` 和当前项目的 `monitor_minerd.py` 都监听：

```text
/tmp/minerd.sock
```

socket 数据是按换行分隔的 JSON event。

已确认 Python 层会关心：

```text
StatisticsEvent
payload.statistics.uptime
payload.statistics.hashrate.5min
payload.statistics.hashrate.15min
payload.statistics.hashrate.60min
```

当前监控脚本还尝试解析：

```text
ShareSubmitEvent
payload.share.work_id
payload.share.nonce
payload.result
```

这些事件可以帮助判断硬件是否真的在跑，但它们不是 ASIC transport 协议本身。

### 22.5 对 ESP32 / Raspberry Pi 5 驱动可行性的更新判断

#### Raspberry Pi 5

树莓派 5 方向相对更可行，因为：

```text
1. 仍是 Linux 环境
2. 可以运行 Python/two1 工具
3. 可以访问 /proc/device-tree
4. 可以运行用户态守护进程
5. GPIO/SPI/I2C/UART 都有 Linux 驱动路径
```

但关键风险：

```text
1. 旧版 minerd 是否能在 Pi 5 / 新系统上运行未知
2. HAT EEPROM overlay 是否兼容未知
3. 如果 minerd 依赖旧内核接口或旧库，可能需要移植
4. 若 minerd 是闭源二进制，则很难直接改到 Pi 5
```

当前可靠结论：

```text
Pi 5 可以作为复现、抓包、上层协议开发平台。
Pi 5 能否直接驱动 21 ASIC，取决于 minerd 是否能运行或我们是否成功复现 ASIC transport。
```

#### ESP32 / ESP32-S3

ESP32 方向适合最终做独立控制器，但必须先知道 ASIC transport 协议。

ESP32 可承担：

```text
1. Wi-Fi 连接矿池或本地代理
2. Stratum/Swirl 适配
3. SPI/UART/I2C 控制
4. 温度/风扇/状态灯控制
5. 轻量 JSON 或二进制协议解析
```

ESP32 暂时不能可靠承担：

```text
1. 直接驱动 21 ASIC，因为帧格式未知
2. 完整替代 minerd，因为 minerd 内部 ASIC 命令未知
3. 在没有外部存储/优化的情况下承载复杂 Python/two1 兼容层
```

当前可靠结论：

```text
ESP32-S3 硬件能力大概率够做控制器。
但在 ASIC transport 未破解前，它只能做上层实验、抓包辅助或未来移植目标，不能保证现在直接驱动模块。
```

### 22.6 后续最优路线

为了让项目开源后可靠推进，建议下一步按优先级做：

```text
P0：拿到原装可运行环境中的 minerd
P0：确认 /tmp/minerd.sock 实际事件样本
P0：用逻辑分析仪抓 HAT 通信总线
P1：同时记录 Swirl work 字段和总线波形
P1：用 asic_trace_correlator.py 匹配 header/midstate/nonce
P2：复现最小 ASIC 初始化序列
P2：复现 work 下发和 nonce 返回
P3：移植到 Pi 5
P4：移植到 ESP32-S3
```

### 22.7 本轮结论

```text
现在已经能明确分层：

two1 Python:
  可读、可修改、可复现 Swirl/Bitcoin work 构造。

minerd:
  是硬件挖矿关键程序，负责真正驱动 21 HAT/ASIC。
  当前只有启动方式和 socket 状态事件线索，没有内部源码。

ASIC transport:
  仍然未知。
  需要从原机运行时抓包反推。

所以当前项目最可靠的技术策略是：
先把上层 work 构造工具做扎实，再用真实抓包把未知的 transport 层补出来。
```

---

## 第二十三轮资料补充：安装包、doctor 检查与 minerd 来源边界（2026-06-16 19:45）

本轮继续检查 `two1` 包的安装配置、诊断工具和默认服务地址，目的是确认 `minerd` 是否随 Python 包发布，以及 21 工具链如何判断系统是否完整。

### 23.1 `setup.py` 确认：Python 包不提供 minerd/minertop

`two1_source/two1-3.10.9/setup.py` 的 `console_scripts` 只安装：

```text
two1
21
twentyone
wallet
channels
```

没有安装：

```text
minerd
minertop
```

`package_data` 中也没有看到 `minerd`、`minertop`、systemd service、init script 或 ASIC 驱动相关文件。

因此可以确认：

```text
当前 two1 Python 包不是完整的 21 Bitcoin Computer 硬件驱动包。
它只是 CLI、钱包、Swirl work/share、支付通道、market/sell 工具等上层组件。
```

这也解释了为什么源码里能看到 `sudo minerd ...`，但找不到 `minerd` 的实现。

### 23.2 `doctor.py` 确认：minerd 是外部系统依赖

`two1/commands/doctor.py` 中有专门检查项：

```text
check_BC_minerd_cli()
```

其逻辑是：

```text
minerd_cli = shutil.which("minerd")
如果能在 PATH 中找到 minerd:
    PASS
否则:
    FAIL, "minerd not installed"
```

这说明 `two1 doctor BC` 只是检查系统里有没有 `minerd` 二进制，并不负责安装或内置该程序。

对项目的意义：

```text
要真正驱动原 21 HAT，必须找到原装系统镜像、deb 包、二进制备份，或从运行中的设备提取 minerd。
仅安装 PyPI/two1 源码包，不足以驱动 ASIC。
```

### 23.3 默认矿池地址与 Swirl transport

`two1/__init__.py` 中确认：

```text
TWO1_POOL_URL = os.environ.get('TWO1_POOL_URL', 'swirl+tcp://grid.21.co:21006')
```

含义：

```text
1. 21 的默认 mining pool transport 名称是 swirl+tcp
2. 默认主机是 grid.21.co
3. 默认端口是 21006
4. 可通过环境变量 TWO1_POOL_URL 覆盖
```

这和前面 `swirl_pb3.py`、`message_factory.py` 的 protobuf work/share 结构能互相对应。

需要注意：

```text
grid.21.co / api.21.co / 21.co 是历史服务地址。
这些服务现在是否仍可用不能假设。
开发本项目时，应把 Swirl 当作可复现的历史协议结构，而不是依赖官方服务仍在线。
```

### 23.4 `doctor.py` 的硬件诊断项

`doctor.py` 中和硬件相关的检查包括：

```text
check_BC_has_chip()
check_BC_minerd_cli()
check_server_21_pool()
```

对应含义：

| 检查项 | 检查内容 | 对本项目的意义 |
|---|---|---|
| `Has Mining Chip` | 读取 HAT device tree 判断是否有 21 mining chip | 判断系统是否识别 HAT |
| `Minerd` | PATH 中是否存在 `minerd` | 判断硬件守护进程是否安装 |
| `21 Pool` | 是否能连默认 pool URL | 判断历史 21 pool 是否可达 |

这给树莓派实机测试提供了明确检查顺序：

```bash
21 doctor BC
which minerd
which minertop
cat /proc/device-tree/hat/product 2>/dev/null
cat /proc/device-tree/hat/uuid 2>/dev/null
```

### 23.5 对“现在能不能驱动”的更精确回答

现在能做到：

```text
1. 识别 two1 Python 层如何判断 HAT 存在
2. 复现 Swirl work/share protobuf 解码
3. 复现 CPU mining 的 block header 构造
4. 复现 Bitshare coinbase padding 和 midstate 相关路径
5. 监听 /tmp/minerd.sock 的 JSON 状态事件
6. 设计抓包字段匹配器
```

现在还不能保证做到：

```text
1. 直接从 Python 驱动 ASIC
2. 直接从 ESP32 驱动 ASIC
3. 在 Pi 5 上直接运行旧 minerd
4. 复刻 minerd 内部的 ASIC 初始化命令
5. 复刻 HAT 到 ASIC 的 work 下发和 nonce 返回帧格式
```

新增证据使结论更明确：

```text
缺的不是 Bitcoin 算法。
缺的不是 Swirl work 字段。
缺的是 minerd 内部或 HAT 总线上的 ASIC transport。
```

### 23.6 寻找 minerd 的合法路径

为了避免侵犯知识产权，后续寻找 `minerd` 应坚持以下原则：

```text
允许：
  1. 从自己拥有的原装设备/SD 卡备份中提取
  2. 记录文件名、版本、hash、依赖库
  3. 观察运行行为和外部通信
  4. 记录自己抓到的总线波形
  5. 写兼容实现，但不复制闭源二进制代码

不建议：
  1. 在开源仓库上传闭源 minerd 二进制
  2. 复制未授权反编译代码
  3. 直接搬运第三方私有资料
```

开源仓库中可以这样写：

```text
This project does not distribute the original 21 minerd binary.
Users may inspect their own legally obtained 21 Bitcoin Computer system image
and contribute clean-room observations, traces, and independently written tools.
```

### 23.7 原机提取清单

如果后续能拿到原装 SD 卡或仍能启动的原机，优先保存：

```bash
which minerd
which minertop
minerd --help
minerd --version
ldd "$(which minerd)"
sha256sum "$(which minerd)"
sha256sum "$(which minertop)"
dpkg -S "$(which minerd)"
dpkg -l | grep -i '21\|miner\|minerd\|bitshare'
systemctl list-unit-files | grep -i 'miner\|minerd\|21'
find /etc -iname '*miner*' -o -iname '*minerd*'
find /usr -iname '*miner*' -o -iname '*minerd*'
```

同时保存运行时状态：

```bash
cat /proc/device-tree/hat/product 2>/dev/null
cat /proc/device-tree/hat/uuid 2>/dev/null
i2cdetect -y 1
ls -l /tmp/minerd.sock /run/minerd.pid
sudo journalctl -u minerd --no-pager
```

### 23.8 本轮结论

```text
two1 Python 包已经证明：
  它不包含 minerd/minertop。
  它把 minerd 当作外部系统命令调用。
  它通过 doctor 检查 minerd 是否存在。
  它通过 /tmp/minerd.sock 读取硬件挖矿状态。

所以后续真正突破点有两个：
1. 找到合法来源的原装 minerd 运行环境。
2. 在原装环境运行时抓 HAT 总线，反推 ASIC transport。
```

---

## 第二十四轮资料补充：现有硬件照片复核与芯片丝印线索（2026-06-16 20:05）

本轮直接复核 `图片/` 目录下的 6 张硬件照片，补充能从照片中确认的板级信息、芯片线索和仍需实测的内容。

### 24.1 已确认照片文件

```text
图片/image_editor_1781509814177.jpg
图片/image_editor_1781509820096.jpg
图片/image_editor_1781509825746.jpg
图片/image_editor_1781509830306.jpg
图片/image_editor_1781509835478.jpg
图片/image_editor_1781509839332.jpg
```

这些图片看起来是同一块 21 Bitcoin Computer HAT/模块的不同角度照片，包括：

```text
1. 外壳与整机视角
2. PCB 正面整体
3. 40-pin 与 DC jack 区域
4. 风扇/散热器结构
5. U1/U9/U12/U15 周边局部
6. U15 核心芯片裸露近照
```

### 24.2 PCB 板级信息（照片确认）

从 `image_editor_1781509820096.jpg` 可见：

```text
21, Inc. Model 21BC1
The 21 Bitcoin Computer
830-0016-01
Rev 9
S/N 010
```

这说明当前板卡至少可以在文档中标为：

```text
Board: 21, Inc. Model 21BC1
PCB: 830-0016-01
Revision: Rev 9
Observed serial label: S/N 010
```

注意：`S/N 010` 可能是照片中这块板的编号，不应写成所有板卡通用编号。

### 24.3 U9：AVCH16T245 电平转换器线索增强

在 `image_editor_1781509835478.jpg` 中，U9 附近顶标能看到类似：

```text
AVCH16T245
```

这比此前“AVCH16T245 类电平转换器”的推测更强。后续可以把 U9 暂记为：

```text
U9: AVCH16T245-family dual-supply bus transceiver / level translator
证据等级：照片可读丝印，仍建议用高清近照和数据手册 pinout 复核
```

工程意义：

```text
1. ASIC 侧和树莓派侧之间很可能存在电压域隔离/电平转换。
2. 必须确认 VCCA/VCCB。
3. 必须确认 DIR/OE 由谁控制。
4. 抓包时要确认逻辑分析仪接在哪一侧，避免电平不匹配。
```

### 24.4 U12：MCP23008 仍需更清晰确认

照片中 U12 位于 40-pin 下方左侧，封装和位置符合 I2C I/O 扩展器的判断，但当前照片顶标不够清晰。

现阶段应写为：

```text
U12: MCP23008? / I2C GPIO expander candidate
状态：照片推测 + 前期资料推断，仍需高清正面照片或实测确认
```

确认方法：

```text
1. 对 U12 拍正面高清微距照片，读完整顶标。
2. 用万用表确认 U12 的 SDA/SCL 是否连到 40-pin Pin 3/Pin 5。
3. 上电后运行 i2cdetect -y 1。
4. 如果出现 0x20-0x27 之间地址，再只读寄存器。
```

### 24.5 U15：核心 ASIC 裸片/封装标记

`image_editor_1781509839332.jpg` 是目前最关键的照片。它显示 U15 位置的核心芯片已经露出，可见大面积绿色基板、中心裸露 die/金属盖区域，以及周围大量去耦电容。

照片中可读或疑似可读标记包括：

```text
U15
H62819 01 Y0C20    （底部一行，可能存在误读）
001                （右下角）
45DC400            （上方/倒置方向，可能存在误读）
SOMA?              （左侧竖排或图形文字，可能存在误读）
```

重要结论：

```text
这些标记目前不能直接等同为公开 ASIC 型号。
在线搜索 H62819 / 45DC400 / 830-0016-01 / Model 21BC1 未找到可确认对应资料。
因此 U15 仍应记录为 21 Bitshare / 21BC1 mining ASIC candidate，而不是写成确定型号。
```

### 24.6 U15 周边电路观察

从 U15 近照可见：

```text
1. U15 周围有大量 C171/C172/C174/C175/C177/C180/C181/C187/C188/C190/C191/C192/C193/C200-C203 等电容。
2. 这符合高电流数字 ASIC 需要密集去耦的特征。
3. U15 周边走线密集，右侧有多组平行走线，可能连接到总线/电平转换/主控接口。
4. U15 位于散热器覆盖区域，正常工作需要散热器和风扇。
```

不能从照片直接确认：

```text
1. ASIC core voltage
2. I/O voltage
3. 时钟输入频率
4. 复位/使能脚
5. SPI/UART/并行总线具体脚位
6. 是否单芯片内含多核 SHA-256 pipeline
```

### 24.7 风扇与散热风险

`image_editor_1781509825746.jpg` 和 `image_editor_1781509830306.jpg` 显示模块带主动风扇和散热器风道。

因此测试原则应更新为：

```text
1. 不要在拆掉散热器/风扇的状态下长时间运行 minerd。
2. 裸芯片拍照后，重新装回散热器并确认导热垫/导热膏接触。
3. 第一次上电应限流，短时观察温升。
4. 如果能读到温度事件，只把它当作参考，仍要手摸/热像/温度计确认异常发热。
```

### 24.8 建议新增硬件资料表

后续开源文档中建议加入：

| RefDes | 照片证据 | 当前识别 | 可信度 | 下一步 |
|---|---|---|---|---|
| U15 | 裸芯片近照 | 21 mining ASIC / Bitshare candidate | 中 | 查高清丝印、测电源、抓总线 |
| U9 | 顶标可见 `AVCH16T245` | 电平转换/总线收发器 | 中高 | 测 VCCA/VCCB、DIR/OE |
| U12 | 封装位置和前期资料 | MCP23008? | 中 | 高清顶标、I2C 扫描 |
| J1 | DC jack | 外部供电输入 | 高 | 测输入电压、电流 |
| 40-pin | Raspberry Pi HAT header | 主机接口 | 高 | 对照 Pin 3/5/19/21/23/24 |
| TPxx | 多个测试点 | 未知信号/电源 | 低 | 编号、测电压、抓波形 |

### 24.9 对协议逆向的帮助

照片复核后，抓包优先级可以更精确：

```text
1. 先抓 40-pin 侧 I2C：确认 HAT EEPROM / MCP23008 / 控制初始化。
2. 再抓 U9 两侧：判断哪些信号经过 AVCH16T245。
3. 对 U9 的 DIR/OE 做静态电平测量。
4. 如果 U9 某侧连到 U15，优先把逻辑分析仪接在树莓派侧，避免未知 ASIC I/O 电压。
5. 对 U15 周边疑似时钟线、复位线、数据线做被动探测。
```

### 24.10 本轮结论

```text
照片已经确认：
  板卡型号：21, Inc. Model 21BC1
  PCB 编号：830-0016-01 Rev 9
  核心位置：U15
  U15 可见芯片标记：H62819 01 Y0C20 / 001 / 45DC400 等疑似字符
  U9 很可能是 AVCH16T245 电平转换器
  模块需要主动散热

照片仍不能确认：
  U15 的公开 ASIC 型号
  U15 的通信协议
  U15 的供电电压
  MCP23008 的真实地址和 GP 位功能

所以硬件资料下一步不是继续猜型号，而是：
  高清丝印 + 万用表追线 + I2C 只读 + 逻辑分析仪抓包。
```

---

## 第二十五轮实际产出：离线解码与只读硬件辅助脚本（2026-06-16 20:35）

本轮不再只补资料，开始落地可执行工具。新增目录：

```text
scripts/
```

当前新增文件：

```text
scripts/decode_swirl_message.py
scripts/bitshare_padding_calc.py
scripts/asic_trace_correlator.py
scripts/read_mcp23008.py
scripts/README.md
```

### 25.1 `decode_swirl_message.py`

作用：

```text
离线解码 21 Swirl protobuf 消息。
支持 server/client 两类消息。
支持 hex/base64/text/file 输入。
支持自动处理 2-byte big-endian length header。
```

重要实现点：

```text
1. 如果本机安装了 google.protobuf，会优先尝试使用 two1_source 中的 swirl_pb3.py 解析。
2. 如果没有 protobuf，自动回退到脚本内置的轻量 Swirl wire decoder。
3. 因此当前开发机即使没有 google.protobuf，也可以解码已知 Swirl 字段。
```

已验证命令：

```bash
python scripts/decode_swirl_message.py --help
python scripts/decode_swirl_message.py --kind client --decoder builtin --length-header none a2060908011201751a026964
```

验证结果：

```json
{
  "kind": "client",
  "decoder": "builtin",
  "message_type": "auth_request",
  "payload_size": 12,
  "decoded": {
    "hardware": 1,
    "username": "u",
    "uuid": "id"
  }
}
```

### 25.2 `bitshare_padding_calc.py`

作用：

```text
复现 two1 源码中的 Bitshare coinbase padding 规则。
输入 client_serialize 后的长度，输出需要补多少字节，以及 padding hex。
```

已验证命令：

```bash
python scripts/bitshare_padding_calc.py --client-serialize-len 100
```

验证结果说明：

```text
100 bytes = 800 bits
补 28 bytes 后变成 128 bytes = 1024 bits
1024 bits 可被 512 bits 整除
```

输出中的 padding：

```text
1b + 27 个 00
```

这符合 `required_padding_for_bitshare()` 中：

```text
bytes([num_bytes_padding - 1]) + bytes(num_bytes_padding - 1)
```

### 25.3 `asic_trace_correlator.py`

作用：

```text
把已知 work 字段拿去扫描 ASIC/HAT 抓包字节流。
它不需要知道完整协议，先找字段在 trace 里的偏移。
```

支持匹配：

```text
direct
byte_reversed
word32_byte_reversed
```

这对 Bitcoin/ASIC 抓包特别有用，因为字段可能以不同端序出现。

已验证命令：

```bash
python scripts/asic_trace_correlator.py trace.hex --trace-format hex --field version=20000000
```

验证结果显示：

```text
如果 trace 中出现 00000020，会在 byte_reversed / word32_byte_reversed 中报告偏移。
```

### 25.4 `read_mcp23008.py`

作用：

```text
在 Raspberry Pi/Linux SBC 上只读 MCP23008 寄存器。
```

默认：

```text
bus = 1
addr = 0x20
mode = read-only
```

读取寄存器：

```text
IODIR  = 0x00
IPOL   = 0x01
GPINTEN= 0x02
DEFVAL = 0x03
INTCON = 0x04
IOCON  = 0x05
GPPU   = 0x06
INTF   = 0x07
INTCAP = 0x08
GPIO   = 0x09
OLAT   = 0x0A
```

安全边界：

```text
脚本不写任何寄存器。
优先使用 smbus2。
如果没有 smbus2，则调用 i2cget 逐寄存器读取。
```

使用示例：

```bash
python scripts/read_mcp23008.py --bus 1 --addr 0x20
```

### 25.5 本轮验证

本轮已执行：

```bash
python scripts/decode_swirl_message.py --help
python scripts/bitshare_padding_calc.py --client-serialize-len 100
python scripts/asic_trace_correlator.py --help
python scripts/read_mcp23008.py --help
python -m py_compile scripts/decode_swirl_message.py scripts/bitshare_padding_calc.py scripts/asic_trace_correlator.py scripts/read_mcp23008.py
```

验证结论：

```text
4 个脚本语法检查通过。
Bitshare padding 计算通过。
Swirl 内置解码器可在无 protobuf 环境下工作。
ASIC trace 字段匹配器可识别端序变体。
MCP23008 脚本只验证 help/语法，未在当前 Windows 环境访问硬件。
```

### 25.6 当前工具链状态

| 工具 | 状态 | 是否碰硬件 | 用途 |
|---|---|---|---|
| `decode_swirl_message.py` | 可用初版 | 否 | Swirl work/share 离线解码 |
| `bitshare_padding_calc.py` | 可用初版 | 否 | Bitshare padding 计算 |
| `asic_trace_correlator.py` | 可用初版 | 否 | 抓包字段偏移匹配 |
| `read_mcp23008.py` | 可用初版 | 只读 I2C | MCP23008 寄存器 dump |

### 25.7 下一步实际开发任务

```text
1. 为 decode_swirl_message.py 增加 WorkNotification 示例输入。
2. 增加 compact_block_builder.py，把 work 字段转成 block header。
3. 增加 capture_fields_template.json，统一 trace 匹配字段格式。
4. 在树莓派实机上跑 read_mcp23008.py，保存输出。
5. 等有逻辑分析仪 trace 后，用 asic_trace_correlator.py 做第一轮字段定位。
```

---

## 第二十六轮实际产出：CompactBlock 构造器与抓包闭环示例（2026-06-16 21:00）

本轮继续把资料变成工具，新增：

```text
scripts/compact_block_builder.py
examples/work_notification_minimal.json
examples/capture_fields_template.json
examples/generated_trace_fields.json
examples/generated_header.hex
```

### 26.1 `compact_block_builder.py`

作用：

```text
把 Swirl WorkNotification 风格的 JSON 字段转换成：
  coinbase transaction
  coinbase double-SHA256 hash
  merkle root
  80-byte block header
  header_first64
  header_tail16
  target / pool target
  block hash
  trace_fields JSON
```

该脚本只使用 Python 标准库：

```text
hashlib
json
struct
argparse
```

不依赖 `two1` 包、不依赖 protobuf、不访问硬件。

### 26.2 输入格式

新增最小示例：

```text
examples/work_notification_minimal.json
```

字段结构和 Swirl `WorkNotification` 对齐：

```text
work_id
version
prev_block_hash
height
nbits
ntime
coinb1
coinb2
merkle_edge
new_block
bits_pool
```

注意：

```text
prev_block_hash 当前按 two1 源码的 internal byte order 输入。
merkle_edge 每项也按 internal byte order 输入。
```

### 26.3 运行示例

已验证命令：

```bash
python scripts/compact_block_builder.py examples/work_notification_minimal.json \
  --enonce1 01020304 \
  --enonce2 00000001 \
  --nonce 0 \
  --fields-out examples/generated_trace_fields.json \
  --trace-out examples/generated_header.hex
```

输出会包含：

```text
coinbase
coinbase_hash_internal / coinbase_hash_rpc
merkle_root_internal / merkle_root_rpc
block_header
header_first64
header_tail16
block_hash_internal / block_hash_rpc
meets_block_target
meets_pool_target
```

### 26.4 生成的抓包匹配字段

`examples/generated_trace_fields.json` 可直接作为 `asic_trace_correlator.py` 的输入。

它包含：

```text
version_le
prev_block_hash_internal
prev_block_hash_rpc
coinbase_hash_internal
coinbase_hash_rpc
merkle_root_internal
merkle_root_rpc
ntime_le
nbits_le
nonce_le
block_header
header_first64
header_tail16
block_hash_internal
block_hash_rpc
```

这正好对应后续真实 HAT/ASIC 抓包时要找的候选字段。

### 26.5 抓包匹配闭环验证

已验证命令：

```bash
python scripts/asic_trace_correlator.py examples/generated_header.hex \
  --trace-format hex \
  --fields-json examples/generated_trace_fields.json \
  --min-field-size 4
```

验证结果重点：

```text
block_header direct offset: 0
header_first64 direct offset: 0
header_tail16 direct offset: 64
version_le direct offset: 0
prev_block_hash_internal direct offset: 4
merkle_root_internal direct offset: 36
ntime_le direct offset: 68
nbits_le direct offset: 72
```

这说明：

```text
compact_block_builder.py 生成的字段，可以被 asic_trace_correlator.py 正确匹配。
后续只要换成真实 Swirl work 和真实逻辑分析仪 trace，就可以开始做 ASIC transport 反推。
```

### 26.6 `asic_trace_correlator.py` 改进

本轮也改进了匹配器：

```text
1. 空 hex 字段会被跳过，不再造成误匹配。
2. 新增 --min-field-size 参数。
3. 适合配合 capture_fields_template.json 使用。
```

注意：

```text
nonce_le = 00000000 这类短且全零的字段，在真实 trace 中会有很多误匹配。
所以抓包时应优先看：
  header_first64
  header_tail16
  merkle_root
  ntime/nbits 组合
  midstate 候选
```

### 26.7 当前工具链闭环

现在已有一个完整的离线闭环：

```text
WorkNotification JSON
  -> compact_block_builder.py
  -> generated_trace_fields.json
  -> generated_header.hex
  -> asic_trace_correlator.py
  -> 字段偏移报告
```

这条链路是后续逆向 ASIC transport 的基础设施。

### 26.8 下一步

继续实际开发时，优先做：

```text
1. 给 decode_swirl_message.py 增加直接导出 WorkNotification JSON 的选项。
2. 把真实 Swirl 消息解码结果直接喂给 compact_block_builder.py。
3. 增加 midstate 计算/展示；如果没有 SHA256 state 库，则先输出 header_first64 作为 midstate 输入。
4. 增加 Saleae/逻辑分析仪 CSV 转 hex trace 的转换器。
```
