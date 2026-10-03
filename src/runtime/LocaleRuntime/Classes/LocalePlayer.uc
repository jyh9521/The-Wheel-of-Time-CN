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
var LocaleSubtitleClock SubtitleClock;

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
        {
            Log("LocaleRuntime cue " $ NextCue $ " elapsed=" $ Elapsed
                $ " text_length=" $ Len(CueText[NextCue]));
            SubtitleMessage(CueText[NextCue], CueEnd[NextCue] - Elapsed, true);
        }
        NextCue++;
    }
    if (NextCue >= CueCount)
        bSequenceActive = false;
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
        if (SubtitleClock == None)
            SubtitleClock = Spawn(class'LocaleSubtitleClock', Self);
        if (SubtitleClock == None)
        {
            Log("LocaleRuntime clock spawn failed; using original caption");
            SubtitleMessage(Localize(string(S.Outer.Name), string(S.Name),
                string(SubtitlesPackageName), true), MinMessageDuration, true);
            return;
        }
        SubtitleClock.SubtitlePlayer = Self;
        Log("LocaleRuntime sequence start: " $ S $ " count=" $ CueCount);
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
            if (Caption != "" && bSequenceActive)
            {
                Log("LocaleRuntime sequence cancelled by: " $ S);
                bSequenceActive = false;
            }
        }
        Super.ClientHearSound(Actor, Id, S, Slot, SoundLocation, Parameters);
    }
}
