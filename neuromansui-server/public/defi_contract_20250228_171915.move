module temp_addr::my_module {

    // Import necessary functions and types from the Sui framework.
    use sui::object::{new, UID};
    use sui::tx_context::{sender, TxContext};

    ///////////////////////////////////////////////////////////////////////////
    // Error Constants
    ///////////////////////////////////////////////////////////////////////////
    const E_INITIAL_A: u64 = 1;
    const E_INITIAL_B: u64 = 2;
    const E_LIQUIDITY_RATIO: u64 = 100;
    const E_SWAP_A_AMOUNT_ZERO: u64 = 200;
    const E_SWAP_A_NEW_RESERVE_A: u64 = 201;
    const E_SWAP_A_INVARIANT: u64 = 202;
    const E_SWAP_B_AMOUNT_ZERO: u64 = 300;
    const E_SWAP_B_NEW_RESERVE_B: u64 = 301;
    const E_SWAP_B_INVARIANT: u64 = 302;
    const E_COLLECT_FEES: u64 = 400;

    ///////////////////////////////////////////////////////////////////////////
    // Helper Functions
    ///////////////////////////////////////////////////////////////////////////

    // Returns the minimum of two u64 values.
    public fun min(a: u64, b: u64): u64 {
        if (a < b) {
            a
        } else {
            b
        }
    }

    // Computes the integer square root of n using Newton's method.
    public fun sqrt(n: u64): u64 {
        if (n < 2) {
            n
        } else {
            let mut x = n;
            let mut y = (x + 1) / 2;
            while (y < x) {
                x = y;
                y = (x + n / x) / 2;
            };
            x
        }
    }

    ///////////////////////////////////////////////////////////////////////////
    // Data Structures
    ///////////////////////////////////////////////////////////////////////////

    // LiquidityPool stores the state of the pool.
    // Note: Objects with the 'key' ability must have an 'id: UID' field as the first field.
    public struct LiquidityPool has key {
        id: UID,
        reserve_a: u64,
        reserve_b: u64,
        fee_rate: u64,     // Fee rate as a percentage (e.g., 1 means 1% fee)
        fee_a: u64,        // Accumulated fees for TokenA from swaps
        fee_b: u64,        // Accumulated fees for TokenB from swaps
        total_shares: u64, // Total liquidity shares issued
        admin: address     // Admin address allowed to collect fees
    }

    // LPToken represents the liquidity provider's share in the pool.
    // Note: We do not add the drop ability because UID does not support drop.
    public struct LPToken has key {
        id: UID,
        share: u64
    }

    ///////////////////////////////////////////////////////////////////////////
    // Initialization Functions
    ///////////////////////////////////////////////////////////////////////////

    // create_pool initializes a new liquidity pool.
    // The creator provides the initial amounts for TokenA and TokenB and the fee rate.
    // The initial liquidity shares are computed as the square root of (initial_a * initial_b).
    public fun create_pool(
        ctx: &mut TxContext,
        initial_a: u64,
        initial_b: u64,
        fee_rate: u64
    ): (LiquidityPool, LPToken) {
        // Ensure that initial liquidity amounts are positive.
        assert!(initial_a > 0, E_INITIAL_A);
        assert!(initial_b > 0, E_INITIAL_B);
        let initial_shares = sqrt(initial_a * initial_b);

        let pool = LiquidityPool {
            id: new(ctx),
            reserve_a: initial_a,
            reserve_b: initial_b,
            fee_rate: fee_rate,
            fee_a: 0,
            fee_b: 0,
            total_shares: initial_shares,
            admin: sender(ctx)
        };

        let lp_token = LPToken {
            id: new(ctx),
            share: initial_shares
        };

        (pool, lp_token)
    }

    ///////////////////////////////////////////////////////////////////////////
    // Liquidity Management Functions
    ///////////////////////////////////////////////////////////////////////////

    // add_liquidity allows liquidity providers to deposit additional funds into the pool.
    // Liquidity must be provided in the same ratio as the current reserves.
    // Returns an LPToken representing the provider's share.
    public fun add_liquidity(
        ctx: &mut TxContext,
        pool: &mut LiquidityPool,
        amount_a: u64,
        amount_b: u64
    ): LPToken {
        // If the pool already has liquidity, enforce the ratio equality via cross multiplication.
        if (pool.reserve_a != 0 && pool.reserve_b != 0) {
            assert!(amount_a * pool.reserve_b == amount_b * pool.reserve_a, E_LIQUIDITY_RATIO);
        };

        let share: u64 = if (pool.total_shares == 0) {
            sqrt(amount_a * amount_b)
        } else {
            let share_a = amount_a * pool.total_shares / pool.reserve_a;
            let share_b = amount_b * pool.total_shares / pool.reserve_b;
            min(share_a, share_b)
        };

        // Update the pool's state.
        pool.reserve_a = pool.reserve_a + amount_a;
        pool.reserve_b = pool.reserve_b + amount_b;
        pool.total_shares = pool.total_shares + share;

        let lp_token = LPToken {
            id: new(ctx),
            share: share
        };

        lp_token
    }

    // remove_liquidity allows liquidity providers to withdraw their share from the pool.
    // The provider supplies an LPToken and receives amounts of TokenA and TokenB proportionally.
    public fun remove_liquidity(
        pool: &mut LiquidityPool,
        lp: LPToken
    ): (u64, u64) {
        // Destructure LPToken completely to consume it.
        let LPToken { share, id: _dummy } = lp;
        // Calculate the amounts to withdraw based on the provider's share.
        let amount_a = share * pool.reserve_a / pool.total_shares;
        let amount_b = share * pool.reserve_b / pool.total_shares;

        // Update the pool state.
        pool.reserve_a = pool.reserve_a - amount_a;
        pool.reserve_b = pool.reserve_b - amount_b;
        pool.total_shares = pool.total_shares - share;

        (amount_a, amount_b)
    }

    ///////////////////////////////////////////////////////////////////////////
    // Swap Functions
    ///////////////////////////////////////////////////////////////////////////

    // swap_a_to_b allows a user to swap TokenA for TokenB.
    // A fee is deducted from the input amount. The swap uses a constant product pricing formula.
    // Returns the amount of TokenB output.
    public fun swap_a_to_b(
        pool: &mut LiquidityPool,
        amount_in: u64
    ): u64 {
        // Ensure the input amount is positive.
        assert!(amount_in > 0, E_SWAP_A_AMOUNT_ZERO);

        // Calculate fee and net input.
        let fee = amount_in * pool.fee_rate / 100;
        let net_in = amount_in - fee;

        let old_reserve_a = pool.reserve_a;
        let old_reserve_b = pool.reserve_b;

        // Compute the invariant: k = reserve_a * reserve_b.
        let k = old_reserve_a * old_reserve_b;

        let new_reserve_a = old_reserve_a + net_in;
        assert!(new_reserve_a > 0, E_SWAP_A_NEW_RESERVE_A);

        let new_reserve_b = k / new_reserve_a;
        // The output amount is the reduction in the TokenB reserve.
        assert!(old_reserve_b > new_reserve_b, E_SWAP_A_INVARIANT);
        let amount_out = old_reserve_b - new_reserve_b;

        // Update the pool's state.
        pool.reserve_a = new_reserve_a;
        pool.reserve_b = new_reserve_b;
        pool.fee_a = pool.fee_a + fee;

        amount_out
    }

    // swap_b_to_a allows a user to swap TokenB for TokenA.
    // A fee is deducted from the input amount. The swap uses a constant product pricing formula.
    // Returns the amount of TokenA output.
    public fun swap_b_to_a(
        pool: &mut LiquidityPool,
        amount_in: u64
    ): u64 {
        // Ensure the input amount is positive.
        assert!(amount_in > 0, E_SWAP_B_AMOUNT_ZERO);

        let fee = amount_in * pool.fee_rate / 100;
        let net_in = amount_in - fee;

        let old_reserve_b = pool.reserve_b;
        let old_reserve_a = pool.reserve_a;

        let k = old_reserve_a * old_reserve_b;

        let new_reserve_b = old_reserve_b + net_in;
        assert!(new_reserve_b > 0, E_SWAP_B_NEW_RESERVE_B);

        let new_reserve_a = k / new_reserve_b;
        assert!(old_reserve_a > new_reserve_a, E_SWAP_B_INVARIANT);
        let amount_out = old_reserve_a - new_reserve_a;

        // Update the pool's state.
        pool.reserve_b = new_reserve_b;
        pool.reserve_a = new_reserve_a;
        pool.fee_b = pool.fee_b + fee;

        amount_out
    }

    ///////////////////////////////////////////////////////////////////////////
    // Fee Collection Function
    ///////////////////////////////////////////////////////////////////////////

    // collect_fees allows the pool admin to withdraw the accumulated fees.
    // Only the admin (creator) of the pool can invoke this function.
    public fun collect_fees(
        pool: &mut LiquidityPool,
        ctx: &mut TxContext
    ): (u64, u64) {
        let caller = sender(ctx);
        assert!(caller == pool.admin, E_COLLECT_FEES);

        let fees_a = pool.fee_a;
        let fees_b = pool.fee_b;

        // Reset the fee accumulators.
        pool.fee_a = 0;
        pool.fee_b = 0;

        (fees_a, fees_b)
    }
}