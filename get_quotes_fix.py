async def get_quotes(self, market: Market, outcomes: Iterable[Outcome]) -> list[Quote]:
        """
        Fetch orderbook from /markets/{ticker}/orderbook endpoint.
        
        Note: Kalshi requires authentication for real-time orderbook data.
        Without auth, the API returns None for orderbook levels.
        """
        url = f"{self.base_url}/markets/{quote(market.market_id, safe='')}/orderbook"

        # Try authenticated request if keys are available
        if self.kalshi_access_key and self.kalshi_private_key:
            timestamp = str(int(time.time() * 1000))
            signature = self._generate_signature(timestamp, "GET", f"/trade-api/v2/markets/{market.market_id}/orderbook")
            
            headers = {
                "KALSHI-ACCESS-KEY": self.kalshi_access_key,
                "KALSHI-ACCESS-SIGNATURE": signature,
                "KALSHI-ACCESS-TIMESTAMP": timestamp
            }
            
            client = self._get_client()
            r = await retry_with_backoff(
                client.get, self.name, url, headers=headers,
                max_retries=3,
                adapter_name=self.name,
                market_id=market.market_id
            )
        else:
            # Fallback to unauthenticated request
            client = self._get_client()
            r = await retry_with_backoff(
                client.get, self.name, url,
                max_retries=3,
                adapter_name=self.name,
                market_id=market.market_id
            )

        if r.status_code != 200:
            self._logger.error(f"Failed to fetch orderbook for {market.market_id}: {r.status_code}")
            return [Quote(
                outcome_id=o.outcome_id,
                bid=None,
                ask=None,
                mid=None,
                spread=None,
                bid_size=None,
                ask_size=None,
            ) for o in outcomes]

        data = r.json()
        orderbook = data.get("orderbook", {})
        yes_levels = orderbook.get("yes", [])
        no_levels = orderbook.get("no", [])
        
        # Handle None or empty string values (no liquidity or no auth)
        if yes_levels is None or yes_levels == "":
            yes_levels = []
        if no_levels is None or no_levels == "":
            no_levels = []
        
        # If no orderbook data, return empty quotes (demo account limitation)
        if not yes_levels and not no_levels:
            return [Quote(
                outcome_id=o.outcome_id,
                bid=None,
                ask=None,
                mid=None,
                spread=None,
                bid_size=None,
                ask_size=None,
            ) for o in outcomes]

        # Process orderbook levels if available
        quotes = []
        for o in outcomes:
            if o.outcome_id.endswith("_YES"):
                # Best bid is highest price someone will buy at
                best_bid = max([level[1] for level in yes_levels], default=None)
                # Best ask is lowest price someone will sell at  
                best_ask = min([level[0] for level in yes_levels], default=None)
            else:  # NO
                # For NO contracts
                best_bid = max([level[1] for level in no_levels], default=None)
                best_ask = min([level[0] for level in no_levels], default=None)
            
            # Convert to cents and calculate mid/spread
            bid = int(best_bid * 100) if best_bid is not None else None
            ask = int(best_ask * 100) if best_ask is not None else None
            
            mid = None
            if bid is not None and ask is not None:
                mid = (bid + ask) // 2
            
            spread = None
            if bid is not None and ask is not None:
                spread = ask - bid
            
            quotes.append(Quote(
                outcome_id=o.outcome_id,
                bid=bid,
                ask=ask,
                mid=mid,
                spread=spread,
                bid_size=None,
                ask_size=None,
            ))
        
        return quotes
