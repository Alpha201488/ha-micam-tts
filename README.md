# Micam Web TTS — 让米家摄像头说话

Home Assistant 自定义集成（HACS 可导入）。它把一段文字交给 `micam-web` 桥接服务，由服务端用 Edge TTS 合成语音，再推给小米摄像头的喇叭直接播出。

适用于 C700 / C701 / CW700S 这类支持双向对讲的米家摄像头——前提是你已经用 go2rtc（含 Xiaomi MISS 补丁）把对讲通道打通。

## 为什么是「服务」而不是 TTS 实体

Home Assistant 的 `tts` 实体语义是「返回音频文件，由 HA 再播放」。这个后端的行为相反：**它让摄像头自己出声**，音频不会回到 HA。

所以本集成暴露两个服务：

- `micam_tts.speak` — 让摄像头说一段话
- `micam_tts.stop` — 结束相机当前的喇叭会话

如果你需要的是「把文字播到 HA 家里的音箱」，应该用 HA 内置的 Edge TTS；这里解决的是「让门口那台摄像头开口」。

## 安装（HACS）

1. HACS → 右上角菜单 → **Custom repositories**
2. Repository 填 `https://github.com/Alpha201488/ha-micam-tts`
3. Category 选 **Integration**
4. Add → 在 HACS 的 Integrations 列表里找到 **Micam Web TTS** → Download
5. 重启 Home Assistant
6. 设置 → 设备与服务 → **添加集成** → 搜 `Micam Web TTS`

## 配置向导

添加集成时按两步走：

**第一步 · 连接**

| 字段 | 说明 |
|---|---|
| 主机 / IP | micam-web 所在机器，例如 `192.168.10.113` |
| 端口 | HTTP 用 `8080`；HTTPS 用 `8443` |
| 使用 HTTPS | 走 8443 时打开 |
| 校验 SSL 证书 | 自签证书请**关闭**，否则会报证书不受信任 |
| 用户名 / 密码 | 与 micam-web 的登录凭据一致（即容器启动参数 `-user` / `-pass` 里设的那一对，不公开写在文档里） |

点提交时集成会真的去请求一次 `/config`：

- 返回 `{"go2rtc":...,"stream":...}` → 通过，顺手读出流名（默认 `cam_av`，`stop` 服务要用）
- 401 → 提示「用户名或密码不对」
- 连不上 → 提示检查 IP、端口与服务状态

凭据只保存在 Home Assistant 自己的配置存储里，不会写进本仓库。

**第二步 · 默认音色与语速**

音色列表是从服务端 `/tts/voices` 实时拉取的，所以不会出现「选项里有、服务端没有」的错配。语速可选 `-20% / -10% / +0% / +10% / +20% / +30%`。

配置完成后随时可以在「配置」里改这两项。

## 用法

### 服务调用

```yaml
service: micam_tts.speak
data:
  text: 门口有人，出来看一下
  voice: zh-CN-XiaoxiaoNeural
  rate: "+0%"
```

`voice` 和 `rate` 都可以省略，省略即用集成里配的默认值。

### 自动化示例

```yaml
automation:
  - alias: 有人按门铃就播报
    triggers:
      - trigger: state
        entity_id: binary_sensor.门口_人体传感器
        to: "on"
    actions:
      - service: micam_tts.speak
        data:
          text: 有人在门口，稍等一下
```

### 脚本里带停顿

```yaml
sequence:
  - service: micam_tts.speak
    data:
      text: 外卖到了，放门口就行
  - delay: "00:00:06"
  - service: micam_tts.stop
```

## 六个可选音色

| id | 听感 |
|---|---|
| `zh-CN-XiaoxiaoNeural` | 晓晓 · 女声，自然，偏日常 |
| `zh-CN-XiaoyiNeural` | 晓伊 · 女声，活泼 |
| `zh-CN-YunxiNeural` | 云希 · 男声，年轻 |
| `zh-CN-YunjianNeural` | 云健 · 男声，浑厚 |
| `zh-CN-YunyangNeural` | 云扬 · 男声，播报腔 |
| `zh-TW-HsiaoChenNeural` | 曉臻 · 台湾女声 |

## 限制

- **单次 200 字上限**（服务端限制，超了直接 400）
- 播放是「整段合成完再推」，所以点下去到出声有 1–2 秒延迟，这是正常的
- 同一时刻相机只能有一个喇叭会话；正在放音乐时调 `speak` 会抢占
- 语音合成依赖微软 Edge 在线服务，断网就没了

## 排错

| 现象 | 原因 |
|---|---|
| `invalid_auth` | 用户名密码与 micam-web 不一致 |
| `cannot_connect` | IP/端口错、容器没起、或防火墙挡了 |
| HTTPS 报证书错误 | 忘了关「校验 SSL 证书」 |
| 服务成功但没声音 | 相机喇叭静音（MIoT `6.1 mute`）、音量太低（`6.2 volume`），或对讲通道没打通 |
| 声音像「贝利亚」（低哑、拖长） | 对讲链路的分帧/采样率参数不对，检查 micam-web 与 go2rtc 版本 |

## License

MIT
