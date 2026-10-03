// Resource-level subtitle scheduler. Existing player behavior is delegated.
class LocalePlayer expands AesSedai;

var localized string CueText[16];
var string CueSound;
var float CueBegin[16];
var float CueEnd[16];
var int CueCount;
var float SequenceStart;
var int NextCue;
var bool bSequenceActive;

simulated event PostBeginPlay()
{
    Super.PostBeginPlay();
    Log("LocaleRuntime subtitle scheduler active: " $ Self.Class);
}

simulated function AdvanceSubtitles()
{
    local float Elapsed;
    if (!bSequenceActive || !bSubtitles)
        return;
    Elapsed = Level.TimeSeconds - SequenceStart;
    while (NextCue < CueCount && Elapsed >= CueBegin[NextCue])
    {
        if (Elapsed < CueEnd[NextCue])
            SubtitleMessage(CueText[NextCue], CueEnd[NextCue] - Elapsed, true);
        NextCue++;
    }
    if (NextCue >= CueCount)
        bSequenceActive = false;
}

simulated event Tick(float DeltaTime)
{
    Super.Tick(DeltaTime);
    AdvanceSubtitles();
}

simulated event ClientHearSound(actor Actor, int Id, sound S,
    ESoundSlot Slot, vector SoundLocation, vector Parameters)
{
    local bool PreviousSubtitles;
    local string Caption;
    if (bSubtitles && Caps(string(S)) == Caps(CueSound))
    {
        PreviousSubtitles = bSubtitles;
        bSubtitles = false;
        Super.ClientHearSound(Actor, Id, S, Slot, SoundLocation, Parameters);
        bSubtitles = PreviousSubtitles;
        SequenceStart = Level.TimeSeconds;
        NextCue = 0;
        bSequenceActive = true;
        AdvanceSubtitles();
    }
    else
    {
        if (S != None && bSubtitles)
        {
            Caption = Localize(string(S.Outer.Name), string(S.Name),
                string(SubtitlesPackageName), true);
            if (Caption != "")
                bSequenceActive = false;
        }
        Super.ClientHearSound(Actor, Id, S, Slot, SoundLocation, Parameters);
    }
}
