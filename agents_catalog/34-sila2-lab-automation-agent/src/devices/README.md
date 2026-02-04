# Mock Device Container

3つのSiLA2デバイス（HPLC、Centrifuge、Pipette）を統合したgRPCサーバーコンテナ。

## 概要

- **目的**: Lambda gRPC制約の解決
- **プロトコル**: SiLA2 over gRPC
- **ポート**: 50051
- **デバイス**: HPLC, Centrifuge, Pipette

## アーキテクチャ

```
Bridge Container --[gRPC]--> Mock Device Container
                              (1コンテナで3デバイス)
```

## ファイル構成

```
mock_devices/
├── server.py           # 3デバイス統合gRPCサーバー
├── Dockerfile          # 最小構成コンテナ
├── requirements.txt    # grpcio, protobuf
├── proto/              # SiLA2プロトコル定義（ビルド時コピー）
└── README.md
```

## デバイス仕様

### HPLC
- **Type**: HPLC
- **Location**: Lab-A
- **Properties**: temperature, pressure, flow_rate

### Centrifuge
- **Type**: Centrifuge
- **Location**: Lab-B
- **Properties**: speed, temperature, time

### Pipette
- **Type**: Pipette
- **Location**: Lab-C
- **Properties**: volume, speed, tip_type

## ビルド

```bash
./scripts/11_build_mock_device_container.sh
```

## デプロイ

CloudFormation経由でECS Fargateにデプロイ：

```bash
./scripts/12_deploy_bridge_container.sh
```

## Service Discovery

ECS内部DNS: `mock-devices.local:50051`

## リソース

- **CPU**: 256 (.25 vCPU)
- **Memory**: 512 MB
- **Launch Type**: FARGATE

## gRPC API

### ListDevices
全デバイス一覧取得

### GetDeviceInfo
デバイス情報取得

### ExecuteCommand
コマンド実行

## ローカルテスト

```bash
# サーバー起動
python server.py

# 別ターミナルでテスト
cd ../bridge_container
python test_mock_grpc_server.py
```

## 本番展開

将来的にエッジ環境の実機器と置き換え可能：

```
Bridge Container --[gRPC]--> 実機器
                              (HPLC, Centrifuge, Pipette)
```
