module temp_addr::my_module_test {

    // Import the testing framework and the contract to test.
    use sui::tx_context::TxContext;
    use temp_addr::my_module;

    /////////////////////////////////////////////////////////////////
    // Test minting of a SuiCoin.
    /////////////////////////////////////////////////////////////////
    #[test]
    public fun test_mint_coin(tx: &mut TxContext) {
        // Mint a coin with value 200.
        let coin = my_module::mint_coin(200, tx);
        // Verify that the coin has the correct value.
        assert!(my_module::coin_value(&coin) == 200, 1);
    }

    /////////////////////////////////////////////////////////////////
    // Test initialization of the staking pool.
    /////////////////////////////////////////////////////////////////
    #[test]
    public fun test_init_pool(tx: &mut TxContext) {
        // Initialize the staking pool, liquid staking token, and admin resource.
        let (pool, token, admin_cap) = my_module::init_pool(@0x1, tx);
        // Verify that the pool and token begin with zero totals.
        assert!(pool.total_staked == 0, 2);
        assert!(pool.total_liquid_tokens == 0, 3);
        assert!(token.supply == 0, 4);
    }

    /////////////////////////////////////////////////////////////////
    // Test staking and claiming rewards.
    /////////////////////////////////////////////////////////////////
    #[test]
    public fun test_stake_and_claim_rewards(tx: &mut TxContext) {
        // Initialize pool and token.
        let (mut pool, mut token, _admin_cap) = my_module::init_pool(@0x1, tx);
        // Mint a coin of value 100 for staking.
        let coin = my_module::mint_coin(100, tx);
        // Stake the coin with an unlock time of 1000.
        let mut stake_pos = my_module::stake(coin, 1000, &mut pool, &mut token, @0x1, tx);
        // Verify that the pool and token have been updated correctly.
        assert!(pool.total_staked == 100, 5);
        assert!(pool.total_liquid_tokens == 100, 6);
        assert!(token.supply == 100, 7);
        // Claim rewards; expected rewards are 10 (10% of 100).
        let reward = my_module::claim_rewards(&mut stake_pos);
        assert!(reward == 10, 8);
        // The stake position's rewards field should be updated.
        assert!(stake_pos.rewards == 10, 9);
    }

    /////////////////////////////////////////////////////////////////
    // Test successful unstaking after the lock period.
    /////////////////////////////////////////////////////////////////
    #[test]
    public fun test_unstake_happy_path(tx: &mut TxContext) {
        // Initialize pool and token.
        let (mut pool, mut token, _admin_cap) = my_module::init_pool(@0x1, tx);
        // Mint a coin of value 100.
        let coin = my_module::mint_coin(100, tx);
        // Stake the coin with an unlock time of 500.
        let mut stake_pos = my_module::stake(coin, 500, &mut pool, &mut token, @0x1, tx);
        // Claim rewards to accrue additional value.
        let _ = my_module::claim_rewards(&mut stake_pos);
        // Unstake after the unlock period (current time = 1000, which is >= 500).
        let coin_out = my_module::unstake(stake_pos, &mut pool, &mut token, tx, 1000);
        // The returned coin should have a value equal to original stake plus rewards (100 + 10).
        assert!(my_module::coin_value(&coin_out) == 110, 10);
        // Verify that the pool and token totals have been updated to reflect the unstaking.
        assert!(pool.total_staked == 0, 11);
        assert!(pool.total_liquid_tokens == 0, 12);
        assert!(token.supply == 0, 13);
    }

    /////////////////////////////////////////////////////////////////
    // Test unstake failure when the stake is still locked.
    /////////////////////////////////////////////////////////////////
    #[test]
    #[should_abort(my_module::E_NOT_UNLOCKED)]
    public fun test_unstake_not_unlocked(tx: &mut TxContext) {
        // Initialize pool and token.
        let (mut pool, mut token, _admin_cap) = my_module::init_pool(@0x1, tx);
        // Mint a coin of value 50.
        let coin = my_module::mint_coin(50, tx);
        // Stake the coin with an unlock time of 2000.
        let stake_pos = my_module::stake(coin, 2000, &mut pool, &mut token, @0x1, tx);
        // Attempt to unstake before the unlock time (current time = 1000).
        let _ = my_module::unstake(stake_pos, &mut pool, &mut token, tx, 1000);
    }

    /////////////////////////////////////////////////////////////////
    // Test valid delegation to a non-zero validator address.
    /////////////////////////////////////////////////////////////////
    #[test]
    public fun test_delegate_valid(tx: &mut TxContext) {
        // Initialize pool and token.
        let (mut pool, mut token, _admin_cap) = my_module::init_pool(@0x1, tx);
        // Mint a coin of value 100.
        let coin = my_module::mint_coin(100, tx);
        // Stake the coin with an unlock time of 1000.
        let mut stake_pos = my_module::stake(coin, 1000, &mut pool, &mut token, @0x1, tx);
        // Delegate to a valid validator address (@0x2).
        my_module::delegate_to_validator(&mut stake_pos, @0x2);
    }

    /////////////////////////////////////////////////////////////////
    // Test delegation failure when using an invalid (zero) validator address.
    /////////////////////////////////////////////////////////////////
    #[test]
    #[should_abort(my_module::E_INVALID_VALIDATOR)]
    public fun test_delegate_invalid(tx: &mut TxContext) {
        // Initialize pool and token.
        let (mut pool, mut token, _admin_cap) = my_module::init_pool(@0x1, tx);
        // Mint a coin of value 100.
        let coin = my_module::mint_coin(100, tx);
        // Stake the coin with an unlock time of 1000.
        let mut stake_pos = my_module::stake(coin, 1000, &mut pool, &mut token, @0x1, tx);
        // Attempt to delegate to an invalid validator address (@0x0), which should abort.
        my_module::delegate_to_validator(&mut stake_pos, @0x0);
    }
}