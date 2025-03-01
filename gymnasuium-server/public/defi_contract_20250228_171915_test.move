// This file contains comprehensive tests for the my_module Sui Move contract.
// It covers happy paths and edge cases for pool creation, liquidity management,
// swaps, and fee collection.
//
// To run these tests with the Sui Move testing framework, include this file in your tests directory.

module temp_addr::my_module_test {

    use sui::object::{ID, UID};
    use sui::tx_context::{sender, TxContext, dummy_context};
    use temp_addr::my_module::{
        self, create_pool, add_liquidity, remove_liquidity, swap_a_to_b, swap_b_to_a, collect_fees,
        LiquidityPool, LPToken
    };

    ///////////////////////////////////////////////////////////////////////////
    // Helper function to create a dummy TxContext for testing.
    ///////////////////////////////////////////////////////////////////////////
    public fun get_test_context(): TxContext {
        dummy_context()
    }

    ///////////////////////////////////////////////////////////////////////////
    // TEST: create_pool happy path
    //
    // Verifies that the liquidity pool is correctly initialized with the provided
    // initial amounts and fee rate, and that the LP token's share corresponds to the
    // computed square root of (initial_a * initial_b).
    ///////////////////////////////////////////////////////////////////////////
    #[test]
    public fun test_create_pool() {
        let mut ctx = get_test_context();
        let (pool, lp) = create_pool(&mut ctx, 1000, 2000, 1);
        // Check that the pool reserves match the initial inputs.
        assert!(pool.reserve_a == 1000, 1001);
        assert!(pool.reserve_b == 2000, 1002);
        // Check that the LP token's share equals sqrt(1000 * 2000).
        let expected_shares = my_module::sqrt(1000 * 2000);
        assert!(lp.share == expected_shares, 1003);
    }

    ///////////////////////////////////////////////////////////////////////////
    // TEST: add_liquidity happy path with proper ratio
    //
    // Verifies that additional liquidity can be added in the correct ratio. Checks
    // that the pool's reserves and total shares are updated accordingly.
    ///////////////////////////////////////////////////////////////////////////
    #[test]
    public fun test_add_liquidity() {
        let mut ctx = get_test_context();
        let (mut pool, _lp1) = create_pool(&mut ctx, 1000, 2000, 1);
        // Add liquidity maintaining the 1:2 ratio.
        let lp2 = add_liquidity(&mut pool, 500, 1000);
        // Check that the pool reserves have grown appropriately.
        assert!(pool.reserve_a == 1500, 1010);
        assert!(pool.reserve_b == 3000, 1011);
        // Total shares should have increased.
        assert!(pool.total_shares >= lp2.share, 1012);
    }

    ///////////////////////////////////////////////////////////////////////////
    // TEST: add_liquidity edge case of incorrect ratio
    //
    // Attempts to add liquidity with an incorrect ratio, which should cause an abort.
    // The expected abort error code is E_LIQUIDITY_RATIO (100).
    ///////////////////////////////////////////////////////////////////////////
    #[test(should_abort = 100)]
    public fun test_add_liquidity_wrong_ratio() {
        let mut ctx = get_test_context();
        let (mut pool, _) = create_pool(&mut ctx, 1000, 2000, 1);
        // Attempt to add liquidity with amounts that do not satisfy the pool's ratio.
        let _ = add_liquidity(&mut pool, 500, 900);
    }

    ///////////////////////////////////////////////////////////////////////////
    // TEST: remove_liquidity happy path
    //
    // Provides liquidity, then removes it by consuming the LP token.
    // Checks that the withdrawn amounts are proportional and that the pool
    // state is updated accordingly.
    ///////////////////////////////////////////////////////////////////////////
    #[test]
    public fun test_remove_liquidity() {
        let mut ctx = get_test_context();
        let (mut pool, lp) = create_pool(&mut ctx, 1000, 2000, 1);
        // Remove liquidity using the provided LP token.
        let (amount_a, amount_b) = remove_liquidity(&mut pool, lp);
        // Since the entire initial liquidity is removed, the amounts should equal the initial reserves.
        assert!(amount_a == 1000, 1020);
        assert!(amount_b == 2000, 1021);
        // The pool reserves should now be zero.
        assert!(pool.reserve_a == 0, 1022);
        assert!(pool.reserve_b == 0, 1023);
    }

    ///////////////////////////////////////////////////////////////////////////
    // TEST: swap_a_to_b happy path
    //
    // Executes a swap from TokenA to TokenB. Verifies that a positive amount of
    // TokenB is received, and that the pool's reserves and fee accumulators update correctly.
    ///////////////////////////////////////////////////////////////////////////
    #[test]
    public fun test_swap_a_to_b() {
        let mut ctx = get_test_context();
        // Create a pool with equal reserves and 1% fee.
        let (mut pool, _) = create_pool(&mut ctx, 1000, 1000, 1);
        // Swap 100 units of TokenA.
        let amount_out = swap_a_to_b(&mut pool, 100);
        // Ensure the output is positive.
        assert!(amount_out > 0, 1030);
        // Calculate expected new reserve for TokenA after deducting fee (1% fee => fee = 1).
        let fee = 100 * 1 / 100;
        let net_in = 100 - fee;
        let expected_new_reserve_a = 1000 + net_in;
        // New reserve for TokenB is determined by the constant product invariant.
        let k = 1000 * 1000;
        let expected_new_reserve_b = k / expected_new_reserve_a;
        assert!(pool.reserve_a == expected_new_reserve_a, 1031);
        assert!(pool.reserve_b == expected_new_reserve_b, 1032);
        // The fee for TokenA should reflect the deducted fee.
        assert!(pool.fee_a == fee, 1033);
    }

    ///////////////////////////////////////////////////////////////////////////
    // TEST: swap_b_to_a happy path
    //
    // Executes a swap from TokenB to TokenA. Checks that a positive amount of TokenA
    // is received, and that the pool's reserves and fee accumulators update as expected.
    ///////////////////////////////////////////////////////////////////////////
    #[test]
    public fun test_swap_b_to_a() {
        let mut ctx = get_test_context();
        let (mut pool, _) = create_pool(&mut ctx, 1000, 1000, 1);
        // Swap 200 units of TokenB.
        let amount_out = swap_b_to_a(&mut pool, 200);
        assert!(amount_out > 0, 1040);
        let fee = 200 * 1 / 100;
        let net_in = 200 - fee;
        let expected_new_reserve_b = 1000 + net_in;
        let k = 1000 * 1000;
        let expected_new_reserve_a = k / expected_new_reserve_b;
        assert!(pool.reserve_b == expected_new_reserve_b, 1041);
        assert!(pool.reserve_a == expected_new_reserve_a, 1042);
        // The fee for TokenB should reflect the deducted fee.
        assert!(pool.fee_b == fee, 1043);
    }

    ///////////////////////////////////////////////////////////////////////////
    // TEST: swap_a_to_b with zero input (edge case)
    //
    // Attempts to perform a swap with an input of zero, which should trigger an abort.
    // The expected abort error code is E_SWAP_A_AMOUNT_ZERO (200).
    ///////////////////////////////////////////////////////////////////////////
    #[test(should_abort = 200)]
    public fun test_swap_a_to_b_zero() {
        let mut ctx = get_test_context();
        let (mut pool, _) = create_pool(&mut ctx, 1000, 1000, 1);
        let _ = swap_a_to_b(&mut pool, 0);
    }

    ///////////////////////////////////////////////////////////////////////////
    // TEST: collect_fees happy path
    //
    // Simulates fee accumulation via swaps and then collects the fees using the pool admin.
    // Checks that the fees collected are non-zero and that the fee accumulators are reset.
    ///////////////////////////////////////////////////////////////////////////
    #[test]
    public fun test_collect_fees() {
        let mut ctx = get_test_context();
        let (mut pool, _) = create_pool(&mut ctx, 1000, 1000, 1);
        // Perform swaps to accumulate fees.
        let _ = swap_a_to_b(&mut pool, 100);
        let _ = swap_b_to_a(&mut pool, 100);
        // Collect fees as the pool admin.
        let (fees_a, fees_b) = collect_fees(&mut pool, &mut ctx);
        // Ensure that fees have been accumulated.
        assert!(fees_a > 0, 1060);
        assert!(fees_b > 0, 1061);
        // Verify that fee accumulators are reset.
        assert!(pool.fee_a == 0, 1062);
        assert!(pool.fee_b == 0, 1063);
    }
}