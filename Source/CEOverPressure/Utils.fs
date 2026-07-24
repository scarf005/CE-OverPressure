namespace CEOverPressure

open System
open System.Collections.Generic

module internal Utils =
    let tryGet (dict: IDictionary<'Key, 'Value>) key =
        match dict.TryGetValue key with
        | true, value -> Some value
        | false, _ -> None

    let tryMax (source: seq<'T>) =
        use enumerator = source.GetEnumerator()

        if enumerator.MoveNext() then
            let mutable maximum = enumerator.Current

            while enumerator.MoveNext() do
                maximum <- max maximum enumerator.Current

            Some maximum
        else
            None
