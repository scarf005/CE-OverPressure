namespace CEOverPressure

open RimWorld
open UnityEngine
open Verse

type CEOverPressureSettings() =
    inherit ModSettings()

    let mutable enableLogging = false

    member this.EnableLogging
        with get () = enableLogging
        and set v = enableLogging <- v

    override this.ExposeData() = Scribe_Values.Look<bool>(&enableLogging, "enableLogging", false, false)


type CEOverPressureMod(contents: ModContentPack) as this =
    inherit Mod(contents)

    do LongEventHandler.ExecuteWhenFinished(fun () -> this.GetSettings<CEOverPressureSettings>() |> ignore)

    override this.SettingsCategory() = "CE-OverPressure"

    override this.DoSettingsWindowContents(canvas: Rect) =
        let listing = Listing_Standard()
        listing.Begin(canvas)

        let settings = this.GetSettings<CEOverPressureSettings>()
        let mutable logging = settings.EnableLogging

        listing.CheckboxLabeled("Enable debug logging", &logging, "Log overpressure events to the console")

        if logging <> settings.EnableLogging then
            settings.EnableLogging <- logging
            settings.Write()

        listing.End()
