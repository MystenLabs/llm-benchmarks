module 0x0::my_module {

    // Import standard modules.
    use std::string;
    use std::vector;
    use std::signer;

    // Import Sui object module for UID.
    use sui::object::UID;

    ////////////////////////////////////////////////////////////////////////////
    // ERROR CODES
    ////////////////////////////////////////////////////////////////////////////
    const ENOT_CHARACTER_OWNER: u64 = 1;
    const EINSUFFICIENT_CURRENCY: u64 = 2;
    const EINVALID_ITEM_INDEX: u64 = 3;
    const EPARTICIPANT_SELF: u64 = 4;

    ////////////////////////////////////////////////////////////////////////////
    // ENUMERATIONS
    ////////////////////////////////////////////////////////////////////////////

    // Rarity for in-game items with required abilities.
    public enum Rarity has copy, drop, store {
        COMMON,
        RARE,
        EPIC,
        LEGENDARY
    }

    ////////////////////////////////////////////////////////////////////////////
    // RESOURCE DEFINITIONS
    ////////////////////////////////////////////////////////////////////////////

    // GameItem represents an in-game item.
    // For Sui objects, the first field must be a UID.
    public struct GameItem has key, store, drop {
        id: UID,
        rarity: Rarity,
        effect: string::String
    }

    // Character represents a player's character.
    public struct Character has key, store, drop {
        id: UID,
        owner: address,                        // Owner of the character.
        strength: u64,                         // Physical power.
        agility: u64,                          // Speed and evasiveness.
        intelligence: u64,                     // Magical/analytical ability.
        level: u64,                            // Current level.
        experience: u64,                       // Experience points.
        achievements: vector<string::String>,  // Achievement logs.
        inventory: vector<GameItem>,           // Owned items.
        currency: u64                          // In-game currency.
    }

    ////////////////////////////////////////////////////////////////////////////
    // HELPER FUNCTIONS
    ////////////////////////////////////////////////////////////////////////////

    // Simple linear congruential generator (LCG) for pseudo-random number generation.
    // NOTE: Not cryptographically secure; use a verifiable random function in production.
    fun secure_random(seed: u64): u64 {
        let a = 6364136223846793005;
        let c = 1;
        seed * a + c
    }

    // Returns a random number in the range [0, max).
    fun random_in_range(seed: u64, max: u64): u64 {
        let rnd = secure_random(seed);
        rnd % max
    }

    // Asserts that the provided sender is the owner of the character.
    fun assert_character_owner(ch: &Character, sender: address) {
        if (ch.owner != sender) {
            abort ENOT_CHARACTER_OWNER;
        }
    }

    // Attempts to level up the character if enough experience has been accumulated.
    fun try_level_up(ch: &mut Character) {
        // Level-up threshold: current level * 100.
        while (ch.experience >= ch.level * 100) {
            ch.experience = ch.experience - ch.level * 100;
            ch.level = ch.level + 1;
            // Increment attributes on level up.
            ch.strength = ch.strength + 2;
            ch.agility = ch.agility + 2;
            ch.intelligence = ch.intelligence + 2;
            // Record the level-up achievement.
            vector::push_back(&mut ch.achievements, string::utf8(b"Level Up".to_vec()));
        }
    }

    ////////////////////////////////////////////////////////////////////////////
    // PUBLIC ENTRY FUNCTIONS
    ////////////////////////////////////////////////////////////////////////////

    // Create a new character.
    // The returned Character will be published to the sender's account.
    public entry fun create_character(sender: &signer, seed: u64): Character {
        let addr = signer::address_of(sender);
        let id = UID::new(sender);
        // Generate base attributes between 10 and 20.
        let strength = 10 + random_in_range(seed, 11);
        let agility = 10 + random_in_range(seed + 1, 11);
        let intelligence = 10 + random_in_range(seed + 2, 11);
        Character {
            id,
            owner: addr,
            strength,
            agility,
            intelligence,
            level: 1,
            experience: 0,
            achievements: vector::empty(),
            inventory: vector::empty(),
            currency: 100
        }
    }

    // Create a new game item.
    // The returned GameItem will be published to the sender's account.
    public entry fun create_item(sender: &signer, rarity: Rarity, effect: string::String): GameItem {
        let id = UID::new(sender);
        GameItem {
            id,
            rarity,
            effect
        }
    }

    // Adds the given item to the character's inventory.
    public entry fun add_item_to_character(sender: &signer, ch: &mut Character, item: GameItem) {
        let addr = signer::address_of(sender);
        // Ensure sender owns the character.
        assert_character_owner(ch, addr);
        vector::push_back(&mut ch.inventory, item);
    }

    // Simulate combat between two characters.
    // Attacker wins if its computed attack power exceeds defender's defense power.
    public entry fun combat(sender: &signer, attacker: &mut Character, defender: &mut Character, seed: u64): bool {
        let addr = signer::address_of(sender);
        // Verify sender is owner of attacker.
        assert_character_owner(attacker, addr);
        // Prevent self-combat.
        if (attacker.owner == defender.owner) {
            abort EPARTICIPANT_SELF;
        }
        // Calculate attack power.
        let attack_bonus = random_in_range(seed, attacker.strength + 1);
        let attack_power = attacker.strength + attack_bonus + attacker.level * 2;
        // Calculate defense power.
        let defense_bonus = random_in_range(seed + 1, defender.agility + 1);
        let defense_power = defender.agility + defense_bonus + defender.level * 2;
        if (attack_power > defense_power) {
            // Attacker wins.
            let exp_gain = (attack_power - defense_power) + 10;
            attacker.experience = attacker.experience + exp_gain;
            // Transfer 10% of defender's currency as reward.
            let reward = defender.currency / 10;
            if (defender.currency >= reward) {
                defender.currency = defender.currency - reward;
                attacker.currency = attacker.currency + reward;
            }
            vector::push_back(&mut attacker.achievements, string::utf8(b"Victory!".to_vec()));
            try_level_up(attacker);
            true
        } else {
            // Defender wins; apply penalty.
            if (attacker.currency >= 5) {
                attacker.currency = attacker.currency - 5;
                defender.currency = defender.currency + 5;
            }
            vector::push_back(&mut attacker.achievements, string::utf8(b"Defeat in combat.".to_vec()));
            false
        }
    }

    // Trade an item from one character's inventory to another's.
    public entry fun trade_item(sender: &signer, from: &mut Character, to: &mut Character, item_index: u64) {
        let addr = signer::address_of(sender);
        // Ensure sender owns the character transferring the item.
        assert_character_owner(from, addr);
        let len = vector::length(&from.inventory);
        if (item_index >= len) {
            abort EINVALID_ITEM_INDEX;
        }
        let item = vector::remove(&mut from.inventory, item_index);
        vector::push_back(&mut to.inventory, item);
    }

    // Exchange currency between characters.
    public entry fun exchange_currency(sender: &signer, from: &mut Character, to: &mut Character, amount: u64) {
        let addr = signer::address_of(sender);
        // Verify sender owns the character sending currency.
        assert_character_owner(from, addr);
        if (from.currency < amount) {
            abort EINSUFFICIENT_CURRENCY;
        }
        from.currency = from.currency - amount;
        to.currency = to.currency + amount;
    }
}