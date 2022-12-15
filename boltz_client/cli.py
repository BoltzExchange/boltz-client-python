from boltz_client.boltz import BoltzConfig, BoltzClient

def main():
    config = BoltzConfig(network="regtest", api_url="http://localhost:9001", mempool_url="http://localhost:8080")
    try:
        client = BoltzClient(config)
        client.log_config()
    except Exception as e:
        print(str(e))
        raise


if __name__ == "__main__":
    main()
