namespace CEOverPressure

open System
open System.Collections.Generic
open CombatExtended
open HarmonyLib
open RimWorld
open UnityEngine
open Verse

/// Applies blast overpressure effects to pawns near an explosion.
/// Computes peak pressure via the Friedlander model, scales it by room enclosure
/// and ground reflection, then applies stuns and internal injuries to affected pawns.
/// See https://en.wikipedia.org/wiki/Friedlander_equation
module internal Overpressure =
    let private settings = lazy DefDatabase<OverpressureSettingsDef>.AllDefsListForReading[0]

    let private extensionFor (projectile: ThingDef) =
        if isNull projectile then
            None
        else
            match projectile.GetModExtension<OverpressureExtension>() with
            | null -> None
            | extension -> Some extension

    /// Estimates TNT-equivalent yield, preferring an explicit extension value
    /// over the damage-and-radius-based model estimate.
    let private estimateYieldKg parameters damage radius (extension: OverpressureExtension option) =
        match extension with
        | Some value when value.tntEquivalentKg > 0.0f -> value.tntEquivalentKg
        | _ -> PressureModel.estimateYieldKg parameters damage radius

    let private isThermobaric (damageDef: DamageDef) =
        damageDef.isExplosive && not (isNull damageDef.workerClass) && typeof<DamageWorker_Flame>.IsAssignableFrom damageDef.workerClass

    /// Computes the enclosed-room pressure multiplier based on cell count and roof coverage.
    /// More enclosed rooms amplify overpressure through wave reflection.
    let private roomMultiplier (configuration: OverpressureSettingsDef) (room: Room) =
        if isNull room || not room.ProperRoom || room.UsesOutdoorTemperature || room.CellCount <= 0 then
            1.0f
        else
            let cellCount = float32 room.CellCount
            let roofFraction = 1.0f - float32 room.OpenRoofCount / cellCount
            let sizeFactor = Mathf.Sqrt(Mathf.Clamp01(configuration.enclosedReferenceRoomCellCount / cellCount))
            1.0f + (configuration.maximumEnclosedReflectionMultiplier - 1.0f) * roofFraction * sizeFactor

    let private stun (configuration: OverpressureSettingsDef) (pawn: Pawn) peakKPa (instigator: Thing) =
        if not pawn.Dead && not (isNull pawn.stances) && not (isNull pawn.stances.stunner) then
            let stunTicks = Mathf.RoundToInt(Mathf.Clamp(peakKPa, configuration.minimumStunTicks, configuration.maximumStunTicks))
            pawn.stances.stunner.StunFor(stunTicks, instigator)

    let private partsToDamage (configuration: OverpressureSettingsDef) peakKPa partCount =
        let mutable bestThreshold = Single.MinValue
        let mutable result = 0
        let bands = configuration.injuryBands

        for index = 0 to bands.Count - 1 do
            let band = bands[index]

            if not (isNull band) && peakKPa >= band.minimumPressureKPa && band.minimumPressureKPa > bestThreshold then
                bestThreshold <- band.minimumPressureKPa
                result <- if band.maximumParts < 0 then partCount else min band.maximumParts partCount

        result

    /// Applies overpressure injuries to a pawn: stuns at moderate pressure,
    /// damages randomly-selected internal body parts at high pressure.
    let private applyInjuries (configuration: OverpressureSettingsDef) (pawn: Pawn) peakKPa (instigator: Thing) =
        if peakKPa >= configuration.stunThresholdKPa then
            if peakKPa < configuration.injuryThresholdKPa then
                stun configuration pawn peakKPa instigator
            else
                let internalParts = SimplePool<List<BodyPartRecord>>.Get()

                try
                    for part in pawn.health.hediffSet.GetNotMissingParts() do
                        if part.depth = BodyPartDepth.Inside then
                            internalParts.Add part

                    let damagePerPart =
                        Mathf.Clamp(
                            (peakKPa - configuration.damagePressureOffsetKPa) / configuration.damagePressureDivisor,
                            configuration.minimumDamagePerPart,
                            configuration.maximumDamagePerPart
                        )

                    let count = partsToDamage configuration peakKPa internalParts.Count
                    let mutable index = 0

                    while index < count && not pawn.Dead do
                        let selectedIndex = Rand.Range(index, internalParts.Count)
                        let part = internalParts[selectedIndex]
                        internalParts[selectedIndex] <- internalParts[index]
                        internalParts[index] <- part

                        DamageInfo(configuration.injuryDamageDef, damagePerPart, configuration.armorPenetration, -1.0f, instigator, part)
                        |> pawn.TakeDamage
                        |> ignore

                        index <- index + 1

                    stun configuration pawn peakKPa instigator
                finally
                    internalParts.Clear()
                    SimplePool<List<BodyPartRecord>>.Return internalParts

    let private applyToPawn
        (configuration: OverpressureSettingsDef)
        parameters
        center
        (map: Map)
        scanRadius
        yieldKg
        height
        pressureMultiplier
        (blastRoom: Room)
        enclosedMultiplier
        (instigator: Thing)
        (pawn: Pawn)
        =
        if not pawn.Dead && pawn.Spawned && pawn.Position.InHorDistOf(center, scanRadius) && GenSight.LineOfSight(center, pawn.Position, map, true) then
            let distanceCells = max configuration.minimumDistanceCells (pawn.Position.DistanceTo center)
            let mutable peakKPa = PressureModel.peakPressureKPa parameters (distanceCells * parameters.MetresPerCell) yieldKg

            if height < configuration.groundReflectionMaximumHeight then
                peakKPa <- peakKPa * configuration.groundReflectionMultiplier

            if enclosedMultiplier > 1.0f && obj.ReferenceEquals(blastRoom, pawn.GetRoom()) then
                peakKPa <- peakKPa * enclosedMultiplier

            applyInjuries configuration pawn (peakKPa * pressureMultiplier) instigator

    /// Main entry point for blast overpressure effects.
    /// Traverses the map region graph from the explosion center, collects pawns,
    /// and applies pressure-based stuns and internal injuries to each affected pawn.
    let apply (center: IntVec3) (map: Map) (radius: float32) (damageDef: DamageDef) (instigator: Thing) (damage: int) (projectile: ThingDef) (height: float32) =
        if not (isNull map) && center.InBounds map && not (isNull damageDef) then
            let configuration = settings.Value
            let extension = extensionFor projectile

            if not (extension |> Option.exists (fun value -> value.disable)) then
                let hasExplicitYield = extension |> Option.exists (fun value -> value.tntEquivalentKg > 0.0f)

                if hasExplicitYield || (damage > 0 && damageDef.isExplosive) then
                    let parameters = configuration.ModelParameters
                    let yieldKg = estimateYieldKg parameters damage radius extension

                    if yieldKg > 0.0f then
                        let extensionMultiplier =
                            match extension with
                            | Some value when value.pressureMultiplier > 0.0f -> value.pressureMultiplier
                            | _ -> 1.0f

                        let pressureMultiplier = extensionMultiplier * (if isThermobaric damageDef then configuration.thermobaricPressureMultiplier else 1.0f)
                        let scanRadius = max (radius + configuration.scanRadiusPadding) (PressureModel.pressureRangeCells parameters yieldKg)
                        let blastRoom = RegionAndRoomQuery.RoomAt(center, map, RegionType.Set_Passable)
                        let enclosedMultiplier = roomMultiplier configuration blastRoom
                        let maximumRegions = Mathf.CeilToInt(Mathf.PI * scanRadius * scanRadius) + 1

                        let processedPawns = SimplePool<HashSet<Pawn>>.Get()

                        try
                            RegionTraverser.BreadthFirstTraverse(
                                center,
                                map,
                                (fun _ region ->
                                    (isNull region.door || region.door.Open) && center.InHorDistOf(region.extentsClose.ClosestCellTo center, scanRadius)),
                                (fun region ->
                                    let pawns = region.ListerThings.ThingsInGroup(ThingRequestGroup.Pawn)

                                    for index = pawns.Count - 1 downto 0 do
                                        match pawns[index] with
                                        | :? Pawn as pawn when processedPawns.Add pawn ->
                                            applyToPawn
                                                configuration
                                                parameters
                                                center
                                                map
                                                scanRadius
                                                yieldKg
                                                height
                                                pressureMultiplier
                                                blastRoom
                                                enclosedMultiplier
                                                instigator
                                                pawn
                                        | _ -> ()

                                    false),
                                maximumRegions
                            )
                        finally
                            processedPawns.Clear()
                            SimplePool<HashSet<Pawn>>.Return processedPawns

[<HarmonyPatch(typeof<GenExplosionCE>, nameof GenExplosionCE.DoExplosion)>]
module internal GenExplosionCEPatch =
    let Postfix (center: IntVec3, map: Map, radius: float32, damType: DamageDef, instigator: Thing, damAmount: int, projectile: ThingDef, height: float32) =
        Overpressure.apply center map radius damType instigator damAmount projectile height

[<StaticConstructorOnStartup>]
type CEOverPressureBootstrap() =
    static do Harmony("scarf.CombatExtended.OverPressure").PatchAll()
