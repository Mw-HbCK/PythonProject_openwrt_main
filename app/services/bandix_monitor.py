#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenWrt Bandix 流量监控工具
用于监控 OpenWrt 路由器的带宽使用情况
"""
import requests
import json
import sys
import argparse
import configparser
import os
import traceback


def convert_size(size_bytes):
    """
    将字节大小转换为可读格式
    """
    if size_bytes == 0:
        return "0 B"
    size_name = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_name) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f} {size_name[i]}"


def convert_speed(speed_bytes):
    """
    将字节速度转换为可读格式
    """
    if speed_bytes == 0:
        return "0 B/s"
    speed_name = ["B/s", "KB/s", "MB/s"]
    i = 0
    while speed_bytes >= 1024 and i < len(speed_name) - 1:
        speed_bytes /= 1024
        i += 1
    return f"{speed_bytes:.2f} {speed_name[i]}"


def load_config(config_file):
    """
    加载配置文件
    """
    if not os.path.exists(config_file):
        print(f"警告: 配置文件 '{config_file}' 不存在，将使用默认配置或命令行参数")
        return {}
    
    config = configparser.ConfigParser()
    try:
        config.read(config_file, encoding='utf-8')
    except Exception as e:
        print(f"警告: 无法读取配置文件 '{config_file}': {e}，将使用默认配置或命令行参数")
        return {}

    bandix_config = {}
    if "bandix" in config:
        bandix_config = dict(config["bandix"])

    return bandix_config


class BandixMonitor:
    def __init__(self, url="http://10.0.0.1/ubus", username="root", password="password", debug=False, timeout=10):
        self.url = url
        self.username = username
        self.password = password
        self.debug = debug
        self.timeout = timeout
        self.sid = None
        self.session = requests.Session()

    def login(self):
        """
        登录获取 ubus_rpc_session
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call",
            "params": [
                "00000000000000000000000000000000",
                "session",
                "login",
                {
                    "username": self.username,
                    "password": self.password
                }
            ]
        }

        try:
            response = self.session.post(self.url, json=payload, timeout=self.timeout)
            response.raise_for_status()

            if self.debug:
                print(f"登录响应状态码: {response.status_code}")
                print(f"登录响应头: {response.headers}")
                print(f"登录响应内容: {response.text}")

            result = response.json()

            if self.debug:
                print(f"登录响应 JSON: {json.dumps(result, indent=2, ensure_ascii=False)}")

            if result.get("result") and len(result["result"]) >= 2:
                if result["result"][0] == 0:
                    self.sid = result["result"][1]["ubus_rpc_session"]
                    if self.debug:
                        print(f"获取到 SID: {self.sid}")
                    return True
                else:
                    print(f"登录失败: {result['result'][1]}")
                    return False
            else:
                print(f"登录失败: 无效的响应格式")
                if self.debug:
                    print(f"响应结果结构: {list(result.keys())}")
                    if "result" in result:
                        print(f"result 长度: {len(result['result'])}")
                        print(f"result 内容: {result['result']}")
                return False
        except requests.exceptions.ConnectionError as e:
            print(f"登录失败: 无法连接到设备 - {e}")
            return False
        except requests.exceptions.HTTPError as e:
            print(f"登录失败: HTTP 错误 - {e}")
            if self.debug:
                print(f"响应内容: {response.text}")
            return False
        except requests.exceptions.Timeout as e:
            print(f"登录失败: 请求超时 - {e}")
            return False
        except requests.exceptions.RequestException as e:
            print(f"登录失败: 网络错误 - {e}")
            return False
        except json.JSONDecodeError as e:
            print(f"登录失败: 无效的 JSON 响应 - {e}")
            if self.debug:
                print(f"响应内容: {response.text}")
            return False
        except Exception as e:
            print(f"登录失败: 未知错误 - {e}")
            if self.debug:
                traceback.print_exc()
            return False

    def get_status(self):
        """
        获取设备状态信息
        """
        if not self.sid:
            print("请先登录")
            return None

        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "call",
            "params": [
                self.sid,
                "luci.bandix",
                "getStatus",
                {}
            ]
        }

        try:
            response = self.session.post(self.url, json=payload, timeout=self.timeout)
            response.raise_for_status()

            if self.debug:
                print(f"获取状态响应状态码: {response.status_code}")
                print(f"获取状态响应内容: {response.text}")

            result = response.json()

            if self.debug:
                print(f"获取状态响应 JSON: {json.dumps(result, indent=2, ensure_ascii=False)}")

            if result.get("result") and len(result["result"]) >= 2:
                if result["result"][0] == 0:
                    return result["result"][1]
                else:
                    print(f"获取状态失败: {result['result'][1]}")
                    return None
            else:
                print(f"获取状态失败: 无效的响应格式")
                if self.debug:
                    print(f"响应结果结构: {list(result.keys())}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"获取状态失败: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"获取状态失败: 无效的 JSON 响应 - {e}")
            if self.debug:
                print(f"响应内容: {response.text}")
            return None
        except Exception as e:
            print(f"获取状态失败: 未知错误 - {e}")
            if self.debug:
                traceback.print_exc()
            return None

    def get_metrics(self, mac="all"):
        """
        获取流量数据
        """
        if not self.sid:
            print("请先登录")
            return None

        payload = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "call",
            "params": [
                self.sid,
                "luci.bandix",
                "getMetrics",
                {"mac": mac}
            ]
        }

        try:
            response = self.session.post(self.url, json=payload, timeout=self.timeout)
            response.raise_for_status()

            if self.debug:
                print(f"获取流量数据响应状态码: {response.status_code}")
                print(f"获取流量数据响应内容: {response.text}")

            result = response.json()

            if self.debug:
                print(f"获取流量数据响应 JSON: {json.dumps(result, indent=2, ensure_ascii=False)}")

            if result.get("result") and len(result["result"]) >= 2:
                if result["result"][0] == 0:
                    return result["result"][1]
                else:
                    print(f"获取流量数据失败: {result['result'][1]}")
                    return None
            else:
                print(f"获取流量数据失败: 无效的响应格式")
                if self.debug:
                    print(f"响应结果结构: {list(result.keys())}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"获取流量数据失败: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"获取流量数据失败: 无效的 JSON 响应 - {e}")
            if self.debug:
                print(f"响应内容: {response.text}")
            return None
        except Exception as e:
            print(f"获取流量数据失败: 未知错误 - {e}")
            if self.debug:
                traceback.print_exc()
            return None

    def _is_time_series_data(self, metrics_data):
        """
        判断 metrics 数据是否为时间序列数据
        """
        if not metrics_data or len(metrics_data) == 0:
            return False
        first_item = metrics_data[0]
        return isinstance(first_item[0], (int, float)) and first_item[0] > 1000000000000

    def _extract_latest_metric(self, metrics_data):
        """
        从时间序列数据中提取最新的数据点
        """
        for metric in reversed(metrics_data):
            if len(metric) >= 9:
                return metric
        return None

    def _extract_metric_data(self, metrics_data, mac_filter=None):
        """
        从 metrics 数据中提取流量信息
        
        Args:
            metrics_data: metrics 数据列表
            mac_filter: MAC 地址过滤器，用于非时间序列数据（"all" 或具体 MAC 地址）
            
        Returns:
            元组 (metric数据, is_time_series)，如果未找到则返回 (None, False)
        """
        if not metrics_data:
            return None, False

        is_time_series = self._is_time_series_data(metrics_data)

        if is_time_series:
            # 时间序列数据，取最后一个有效数据点
            # 注意：时间序列数据的 MAC 过滤已在 API 调用时完成
            metric = self._extract_latest_metric(metrics_data)
            return metric, True
        else:
            # 非时间序列数据，查找匹配的 MAC 地址
            for metric in metrics_data:
                if len(metric) < 9:
                    continue
                # 如果 mac_filter 为 None，返回第一个有效数据
                # 如果指定了 mac_filter，则匹配对应的 MAC 地址
                if mac_filter is None or metric[0] == mac_filter:
                    return metric, False

        return None, False

    def _extract_metric_dict(self, metric, hostname="未知", ip="-", mac=None, is_time_series=False):
        """
        从 metric 数据中提取信息并返回字典
        
        Args:
            metric: metric 数据列表
            hostname: 设备主机名
            ip: 设备 IP 地址
            mac: MAC 地址（可选）
            is_time_series: 是否为时间序列数据
            
        Returns:
            包含流量信息的字典，如果数据无效则返回 None
        """
        if not metric or len(metric) < 9:
            return None

        # 提取时间戳（如果是时间序列数据，metric[0] 是时间戳）
        timestamp = None
        data_start_idx = 1  # 数据起始索引
        
        if is_time_series and isinstance(metric[0], (int, float)) and metric[0] > 1000000000000:
            timestamp = int(metric[0])  # 时间戳（毫秒）
            data_start_idx = 1
        else:
            # 非时间序列数据，metric[0] 可能是 MAC 地址，没有时间戳
            data_start_idx = 1

        # 提取数据
        down_speed_bytes = metric[data_start_idx]  # 瞬时下行速率 (Bytes/s)
        up_speed_bytes = metric[data_start_idx + 1]  # 瞬时上行速率 (Bytes/s)
        total_down_bytes = metric[data_start_idx + 6]  # 累计下载总量 (Bytes)
        total_up_bytes = metric[data_start_idx + 7]  # 累计上传总量 (Bytes)

        result = {
            "hostname": hostname,
            "ip": ip,
            "mac": mac,
            "down_speed": {
                "bytes_per_second": down_speed_bytes,
                "formatted": convert_speed(down_speed_bytes)
            },
            "up_speed": {
                "bytes_per_second": up_speed_bytes,
                "formatted": convert_speed(up_speed_bytes)
            },
            "total_download": {
                "bytes": total_down_bytes,
                "formatted": convert_size(total_down_bytes)
            },
            "total_upload": {
                "bytes": total_up_bytes,
                "formatted": convert_size(total_up_bytes)
            }
        }
        
        # 如果有时间戳，添加到结果中
        if timestamp is not None:
            result["timestamp"] = timestamp
            # 同时提供可读的时间格式（可选，使用 datetime 模块）
            try:
                from datetime import datetime
                result["timestamp_formatted"] = datetime.fromtimestamp(timestamp / 1000).isoformat()
            except:
                pass
        
        return result

    def get_monitor_data(self):
        """
        获取监控数据并返回字典
        
        Returns:
            包含监控数据的字典，如果登录失败则返回 None
        """
        # 登录
        if not self.login():
            return None

        # 获取设备状态
        status = self.get_status()
        devices = []

        if status and "devices" in status:
            devices = status["devices"]
            if self.debug:
                print(f"设备列表: {json.dumps(devices, indent=2, ensure_ascii=False)}", file=sys.stderr)
        else:
            # 如果无法获取设备状态，继续执行，但只能获取全网数据
            if self.debug:
                print("无法获取设备状态，只能获取全网数据", file=sys.stderr)

        # 收集所有流量数据
        result = {
            "total": None,
            "devices": []
        }

        # 1. 获取全网流量数据
        metrics = self.get_metrics("all")
        if metrics and "metrics" in metrics:
            metrics_data = metrics["metrics"]
            metric, is_time_series = self._extract_metric_data(metrics_data, "all")
            if metric:
                result["total"] = self._extract_metric_dict(metric, "全网总计", "-", "all", is_time_series)

        # 2. 获取每个设备的流量数据
        for device in devices:
            mac = device["mac"]
            hostname = device.get("hostname", "未知")
            ip = device.get("ip", "-")

            # 获取该设备的流量数据
            device_metrics = self.get_metrics(mac)
            if device_metrics and "metrics" in device_metrics:
                device_metrics_data = device_metrics["metrics"]
                metric, is_time_series = self._extract_metric_data(device_metrics_data, mac)
                if metric:
                    device_data = self._extract_metric_dict(metric, hostname, ip, mac, is_time_series)
                    if device_data:
                        result["devices"].append(device_data)
        
        # 添加当前请求时间戳
        try:
            from datetime import datetime
            result["request_timestamp"] = int(datetime.now().timestamp() * 1000)  # 毫秒时间戳
            result["request_timestamp_formatted"] = datetime.now().isoformat()
        except:
            pass

        return result

    def run(self):
        """
        执行监控逻辑并输出 JSON 格式结果
        """
        result = self.get_monitor_data()
        if result is None:
            sys.exit(1)
        
        # 输出 JSON 格式结果
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenWrt bandix 流量监控脚本")
    parser.add_argument("--url", default=None, help="设备 ubus URL")
    parser.add_argument("-u", "--username", default=None, help="登录用户名")
    parser.add_argument("-p", "--password", default=None, help="登录密码")
    parser.add_argument("-c", "--config", default="bandix_config.ini", help="配置文件路径 (默认: bandix_config.ini)")
    parser.add_argument("-d", "--debug", action="store_true", help="启用调试模式")

    args = parser.parse_args()

    # 加载配置文件
    config = load_config(args.config)

    # 设置默认值和优先级：命令行参数 > 配置文件 > 硬编码默认值
    url = args.url or config.get("url", "http://10.0.0.1/ubus")
    username = args.username or config.get("username", "root")
    password = args.password or config.get("password", "password")

    # 检查配置是否完整
    if not username or not password:
        print("错误: 用户名和密码不能为空")
        print("请在配置文件中设置或通过命令行参数指定")
        sys.exit(1)

    monitor = BandixMonitor(
        url=url,
        username=username,
        password=password,
        debug=args.debug
    )
    monitor.run()
