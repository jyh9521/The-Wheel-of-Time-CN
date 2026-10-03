// A separate Actor clock avoids native PlayerPawn tick dispatch differences.
class LocaleSubtitleClock expands Actor;

var LocalePlayer SubtitlePlayer;
var bool bLoggedTick;

simulated event Tick(float DeltaTime)
{
    if (SubtitlePlayer == None || SubtitlePlayer.bDeleteMe)
    {
        Destroy();
        return;
    }
    if (!bLoggedTick)
    {
        Log("LocaleRuntime clock tick active");
        bLoggedTick = true;
    }
    SubtitlePlayer.AdvanceSubtitles();
}

defaultproperties
{
    bHidden=True
    bCollideActors=False
    bCollideWorld=False
    RemoteRole=ROLE_None
}
