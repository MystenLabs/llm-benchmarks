module 0x0::my_module {

    // Import the necessary components from the Sui framework and the standard library.
    use sui::object::UID;
    use sui::tx_context::TxContext;
    use std::vector;

    /////////////////////////////////////////////////////////////////////////
    // Enum for item rarity.
    // We add abilities copy, store, and drop so that this type can be used
    // inside Sui objects.
    /////////////////////////////////////////////////////////////////////////
    public enum Rarity has copy, store, drop {
        Common,
        Uncommon,
        Rare,
        Epic,
        Legendary
    }

    /////////////////////////////////////////////////////////////////////////
    // Sui object representing a game character.
    // IMPORTANT: Sui objects (i.e. structs with the 'key' ability) must have
    // as their first field an id of type sui::object::UID.
    /////////////////////////////////////////////////////////////////////////
    public struct Character has key, store, drop {
        id: UID,                // Must be the first field and of type UID.
        owner: address,
        strength: u64,
        agility: u64,
        intelligence: u64,
        level: u64,
        exp: u64,
        achievements: vector<u64>,
        coins: u64
    }

    /////////////////////////////////////////////////////////////////////////
    // Sui object representing an in-game item.
    /////////////////////////////////////////////////////////////////////////
    public struct GameItem has key, store, drop {
        id: UID,                // Must be the first field.
        rarity: Rarity,
        effect: u64,
        owner: address
    }

    /////////////////////////////////////////////////////////////////////////
    // Sui object representing a listing for a tradable item.
    /////////////////////////////////////////////////////////////////////////
    public struct Listing has key, store, drop {
        id: UID,                // Must be the first field.
        seller: address,
        price: u64,
        // The listing resource owns the game item offered for sale.
        item: GameItem
    }

    /////////////////////////////////////////////////////////////////////////
    // Computes the experience required to reach the next level using a
    // quadratic function.
    /////////////////////////////////////////////////////////////////////////
    fun exp_for_next_level(level: u64): u64 {
        100 * level * level
    }

    /////////////////////////////////////////////////////////////////////////
    // Creates a new game character for the caller.
    // Note: Entry function parameters must be of allowed types. Here we pass
    // the transaction context by value (and then rebind it as mutable locally)
    // to satisfy entry function constraints.
    /////////////////////////////////////////////////////////////////////////
    public entry fun create_character(
        ctx: TxContext,
        strength: u64,
        agility: u64,
        intelligence: u64,
        coins: u64
    ): Character {
        // Rebind the context as mutable for operations that require a mutable reference.
        let mut ctx = ctx;
        let sender = TxContext::sender(&ctx);
        Character {
            id: UID::new(&mut ctx),  // Creates a new unique id.
            owner: sender,
            strength,
            agility,
            intelligence,
            level: 1,
            exp: 0,
            achievements: vector::empty(),
            coins
        }
    }

    /////////////////////////////////////////////////////////////////////////
    // Creates a new game item for the caller.
    // The item's rarity and effect are determined via a pseudo-random function.
    /////////////////////////////////////////////////////////////////////////
    public entry fun create_item(
        ctx: TxContext,
        seed: u64
    ): GameItem {
        let mut ctx = ctx;
        let rand_val = random(seed);
        let rarity_val = determine_rarity(rand_val);
        // Compute effect: base value (10) + random component + bonus from rarity.
        let effect_val = 10 + (rand_val % 50) + rarity_bonus(rarity_val);
        GameItem {
            id: UID::new(&mut ctx),
            rarity: rarity_val,
            effect: effect_val,
            owner: TxContext::sender(&ctx)
        }
    }

    /////////////////////////////////////////////////////////////////////////
    // Determines the rarity based on a pseudo-random number.
    // Distribution:
    //   0-49   : Common
    //   50-74  : Uncommon
    //   75-89  : Rare
    //   90-97  : Epic
    //   98-99  : Legendary
    /////////////////////////////////////////////////////////////////////////
    fun determine_rarity(rand: u64): Rarity {
        let chance = rand % 100;
        if (chance < 50) {
            Rarity::Common
        } else if (chance < 75) {
            Rarity::Uncommon
        } else if (chance < 90) {
            Rarity::Rare
        } else if (chance < 98) {
            Rarity::Epic
        } else {
            Rarity::Legendary
        }
    }

    /////////////////////////////////////////////////////////////////////////
    // Returns a bonus effect value based on the rarity of the item.
    /////////////////////////////////////////////////////////////////////////
    fun rarity_bonus(rarity: Rarity): u64 {
        match (rarity) {
            Rarity::Common => 0,
            Rarity::Uncommon => 5,
            Rarity::Rare => 10,
            Rarity::Epic => 20,
            Rarity::Legendary => 40
        }
    }

    /////////////////////////////////////////////////////////////////////////
    // A simple pseudo-random number generator using XOR shift.
    // Note: This is not cryptographically secure. In production, use the
    // blockchain's secure randomness source.
    /////////////////////////////////////////////////////////////////////////
    fun random(seed: u64): u64 {
        let mut x = seed;
        x = x ^ (x << 13);
        x = x ^ (x >> 7);
        x = x ^ (x << 17);
        x
    }

    /////////////////////////////////////////////////////////////////////////
    // Simulates combat between two characters.
    // The caller must own the attacking character.
    // Combat power is computed using attributes plus a random bonus.
    // On victory, the attacker gains experience and may level up.
    // On defeat, the attacker pays a coin penalty to the defender.
    /////////////////////////////////////////////////////////////////////////
    public entry fun combat(
        ctx: TxContext,
        // Mutable reference because the resource's fields get updated.
        attacker_char: &mut Character,
        defender_char: &mut Character,
        seed: u64
    ) {
        let mut ctx = ctx;
        let caller = TxContext::sender(&ctx);
        // Anti-cheat: Ensure the caller owns the attacking character.
        assert!(attacker_char.owner == caller, 1);

        let rand_attacker = random(seed);
        let rand_defender = random(seed + 1);
        let attacker_power = attacker_char.strength + attacker_char.agility +
                             attacker_char.intelligence + (rand_attacker % 20);
        let defender_power = defender_char.strength + defender_char.agility +
                             defender_char.intelligence + (rand_defender % 20);

        if (attacker_power > defender_power) {
            // Attacker wins: gains experience.
            let exp_gain = 50;
            attacker_char.exp = attacker_char.exp + exp_gain;
            let exp_needed = exp_for_next_level(attacker_char.level);
            if (attacker_char.exp >= exp_needed) {
                attacker_char.level = attacker_char.level + 1;
                attacker_char.exp = attacker_char.exp - exp_needed;
                vector::push_back(&mut attacker_char.achievements, attacker_char.level);
            }
        } else {
            // Defender wins: transfer coin penalty.
            let penalty = 10;
            if (attacker_char.coins >= penalty) {
                attacker_char.coins = attacker_char.coins - penalty;
                defender_char.coins = defender_char.coins + penalty;
            }
        }
    }

    /////////////////////////////////////////////////////////////////////////
    // Lists an item for sale on the in-game economy.
    // Only the owner of the item can list it.
    /////////////////////////////////////////////////////////////////////////
    public entry fun list_item_for_sale(
        ctx: TxContext,
        item: GameItem,
        price: u64
    ): Listing {
        let mut ctx = ctx;
        let seller_addr = TxContext::sender(&ctx);
        // Verify ownership of the item.
        assert!(seller_addr == item.owner, 2);
        Listing {
            id: UID::new(&mut ctx),
            seller: seller_addr,
            price,
            item
        }
    }

    /////////////////////////////////////////////////////////////////////////
    // Purchases a listed item.
    // Transfers the item's ownership to the buyer and consumes the listing.
    /////////////////////////////////////////////////////////////////////////
    public entry fun purchase_item(
        ctx: TxContext,
        listing: Listing
    ): GameItem {
        let mut ctx = ctx;
        let buyer = TxContext::sender(&ctx);
        let mut item = listing.item;  // Move the GameItem out of the Listing.
        item.owner = buyer;
        item
    }
}