# 21BC1 Decoder Design

本文档描述可以基于现有资料实现的解码器范围。

当前可以做的是候选字段解码器和 trace analyzer；还不能声称已经实现
完整的 21BC1 ASIC 私有协议解码器。

## 解码器分层

```text
Layer 0: raw capture bytes
Layer 1: byte order / word order variants
Layer 2: known Bitcoin work fields
Layer 3: Swirl-derived work reconstruction
Layer 4: candidate ASIC frame grouping
Layer 5: confirmed ASIC command decoder
```

目前可靠度：

```text
Layer 0 = 可做
Layer 1 = 可做
Layer 2 = 可做
Layer 3 = 可做
Layer 4 = 半自动推测
Layer 5 = 等真实抓包确认
```

## 第一版目标

脚本名称建议：

```text
scripts/trace_decoder.py
```

第一版功能：

```text
输入:
  .hex
  .bin
  JSON trace fields

输出:
  匹配到的字段名
  偏移
  长度
  字节序变体
  匹配次数
  简单可信度
```

已知字段来源：

```text
examples/generated_trace_fields_midstate.json
```

应该识别：

```text
version_le
prev_block_hash_internal
merkle_root_internal
ntime_le
nbits_le
nonce_le
block_header
header_first64
header_tail16
sha256_midstate_bytes_be
sha256_second_chunk64
sha256_first_pass_128
getwork_data_like_128
block_hash_internal
```

## 候选字节序

至少搜索：

```text
direct
byte_reversed
word32_byte_reversed
```

后续可增加：

```text
word32_order_reversed
word32_byte_reversed_and_order_reversed
little_endian_uint32_value_match
sliding_nonce_match
```

## 可信度规则

高可信：

```text
匹配到 32/64/80/128 字节长字段
同一 trace 中多个字段位置关系合理
字段出现在 minerd work dispatch 时刻
重复 work 中只有 nonce/ntime 等字段变化
```

中可信：

```text
匹配到 merkle_root、midstate、second_chunk 中任意一个
匹配到 ntime + nbits + nonce 的相邻组合
匹配到 32-bit word-swapped header 片段
```

低可信：

```text
只匹配到 4 字节 nonce 或 ntime
只匹配到大量 00/ff 短字段
字段出现在无关启动噪声中
```

## 输出格式建议

JSON 输出示例：

```json
{
  "trace": "capture.hex",
  "trace_size": 4096,
  "matches": [
    {
      "field": "sha256_midstate_bytes_be",
      "offset": 128,
      "size": 32,
      "variant": "word32_byte_reversed",
      "confidence": "high"
    }
  ],
  "hypotheses": [
    "midstate_protocol_candidate"
  ]
}
```

文本摘要示例：

```text
HIGH  offset 0x0080  sha256_midstate_bytes_be  word32_byte_reversed
HIGH  offset 0x00a0  sha256_second_chunk64     direct
HINT  possible protocol: midstate + second chunk
```

## 第二版目标

在有真实抓包后，第二版可以做：

```text
自动找帧边界
识别重复帧头
估计长度字段
估计 CRC/校验字段
识别 work id / sequence id
识别 nonce 返回候选帧
对比多次 work 的差异字段
```

## 第三版目标

当至少有 3 组真实 work + trace + nonce 结果后，可以尝试：

```text
ASIC command dictionary
init frame decoder
work frame decoder
result frame decoder
frequency/config frame decoder
replay safety checker
```

## 当前不能做的事

不能直接输出：

```text
confirmed init command
confirmed ASIC register map
confirmed work frame structure
confirmed nonce result frame
confirmed CRC algorithm
```

这些都必须来自真实抓包和重复验证。

## 与现有脚本关系

已有脚本：

```text
scripts/asic_trace_correlator.py
```

它已经完成第一版解码器的一部分能力：

```text
搜索已知字段
支持 direct / byte_reversed / word32_byte_reversed
输出 JSON 匹配结果
```

下一步可以把它扩展为：

```text
scripts/trace_decoder.py
```

或者继续增强原脚本，避免工具数量太多。
