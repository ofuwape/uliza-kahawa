"""Training examples per intent. SYNTHETIC: hand-written by the team (Kiswahili, English, and the mixed SMS
style farmers actually type: Sheng, no accents, shorthand). Real farmer messages would be better; we have none,
and say so in the report. Kikuyu is NOT here: it is a held-out test only (models/kikuyu_test.jsonl).

Out-of-scope examples ("none") come from MASSIVE (real utterances, CC BY 4.0) at training time, so the model learns
to say "not sure" rather than force an answer.
"""

EXAMPLES = {
    "leaf_rust": [
        "majani ya kahawa yana unga wa njano chini", "madoa ya machungwa chini ya majani", "kutu kwenye majani ya kahawa",
        "majani yana kutu nifanye nini", "majani yanapukutika na yana unga", "unga wa rangi ya chungwa kwenye majani",
        "kahawa yangu ina ugonjwa wa majani", "majani yanageuka njano na kuanguka", "nimeona kutu kwenye miti yangu",
        "leaf rust kwa kahawa", "majani yangu yana rust", "orange powder under the leaves", "yellow spots under coffee leaves",
        "my coffee leaves have rust", "leaves falling off with orange dust", "what is this orange powder on my leaves",
        "rust on coffee what do i do", "coffee leaf rust treatment", "majani yana madoa ya njano na yanaanguka",
        "kahawa majani rust dawa gani", "majan yana kutu", "maajani yana unga njano", "leaves have orange spots underneath",
    ],
    "cbd": [
        "matunda ya kahawa yanageuka meusi", "cheri zinaoza zikiwa mbichi", "madoa meusi kwenye matunda mabichi",
        "matunda yanakauka mtini", "ugonjwa wa matunda ya kahawa", "matunda yanaanguka yakiwa meusi",
        "berries zinakuwa nyeusi", "cbd kwa kahawa yangu", "matunda mabichi yana madoa", "matunda yamekauka na kuwa meusi",
        "black spots on green berries", "my coffee berries are turning black", "berries rotting before they ripen",
        "coffee berry disease", "berries dry and black on the branch", "dark sunken spots on the cherries",
        "green cherries have black marks", "matunda yana doa jeusi", "matund yanaoza", "cherry nyeusi kwa mti",
        "the young berries are dying", "berries dropping black",
    ],
    "berry_borer": [
        "matunda yana matundu madogo", "kuna tundu kwenye cheri", "wadudu ndani ya matunda ya kahawa",
        "kidudu kinatoboa matunda", "matunda yametobolewa", "punje zimeharibika ndani", "mdudu mdogo mweusi ndani ya tunda",
        "matundu kwa ncha ya tunda", "borer kwa kahawa", "small holes in my coffee berries", "tiny hole at the tip of the cherry",
        "insects inside the berries", "beans damaged inside the cherry", "coffee berry borer", "bugs boring into the berries",
        "little black beetle in the coffee berry", "cheri zina mashimo", "matunda yana mashimo madogo",
        "holes kwa berries", "mdudu anaharibu cheri", "matundu kwenye cheri zangu",
    ],
    "spray_timing": [
        "nipige dawa lini", "ninyunyize dawa wakati gani", "dawa ya kutu inapigwa lini", "lini nianze kunyunyiza kabla ya mvua",
        "mara ngapi ninyunyize dawa", "kunyunyizia kahawa msimu wa mvua", "dawa ya shaba ipigwe lini", "wiki ngapi kati ya kunyunyiza",
        "ratiba ya kunyunyiza kahawa", "when should i spray my coffee", "when to spray copper", "how often should i spray fungicide",
        "spray before the rains or after", "spraying schedule for coffee", "which month do i spray", "time to spray for the short rains",
        "nipige copper lini", "spray lini", "dawa lini kabla mvua", "kunyunyiza oktoba", "when to apply fungicide long rains",
    ],
    "yield_drop": [
        "mavuno yangu yamepungua", "kahawa haizai kama zamani", "mbona mavuno yanashuka", "mwaka huu nimepata kilo chache",
        "miti inazaa kidogo", "kwa nini kahawa yangu haizai", "mazao yamepungua sana", "nimevuna kidogo kuliko mwaka jana",
        "sijui kwa nini mavuno ni machache", "kahawa yangu inazaa vibaya", "my yield has dropped", "why is my coffee producing less",
        "fewer berries this season", "harvest is lower than last year", "my coffee yield is going down and i dont know why",
        "trees are not producing much", "less coffee every year", "mavuno yamedrop", "harvest imepungua", "yield iko chini sana",
        "kilo zimepungua", "mazao yanashuka kila mwaka",
    ],
    "fertilizer_weeds": [
        "niweke mbolea gani", "mbolea ya kahawa", "lini niweke mbolea", "magugu mengi kwenye shamba la kahawa",
        "nifanye nini na magugu", "matandazo kwa kahawa", "udongo umekauka", "mbolea inasaidia kahawa", "kiasi gani cha mbolea",
        "which fertilizer for coffee", "when to apply fertilizer", "weeds in my coffee farm", "should i use manure",
        "mulch for coffee", "how much fertilizer per tree", "soil is dry around the trees", "fertilizer gani poa kwa kahawa",
        "manure ama fertilizer", "palilia kahawa", "weeding coffee", "can.fertilizer help my coffee",
    ],
    "pruning": [
        "nipogoe kahawa lini", "kupogoa miti ya kahawa", "miti yangu ni mizee sana", "matawi mengi mazee",
        "nikate shina la mti mzee", "jinsi ya kupogoa kahawa", "miti imekuwa mirefu sana", "kupogoa baada ya mavuno",
        "when should i prune coffee", "how to prune coffee trees", "my coffee bushes are very old", "too many old branches",
        "should i stump my old trees", "cutting back old coffee", "pruning after harvest", "prune lini", "kupogoa kahawa mzee",
        "stumping kahawa", "miti mizee haizai", "old trees pruning",
    ],
    "harvest": [
        "nichume cheri lini", "jinsi ya kuchuma kahawa", "nichume zilizoiva tu", "cheri nyekundu ama kijani",
        "naweza kuchuma cheri mbichi", "mavuno ya kahawa yanaanza lini", "kuchuma kwa mkono", "nichume mara ngapi",
        "when to pick coffee cherries", "how do i pick coffee", "should i pick green cherries", "only pick the red ones",
        "when does the harvest start", "picking coffee by hand", "how many times do i pick", "kuchuma kahawa", "chuma lini",
        "picking ripe cherry", "cheri zimeiva nichume", "harvest time coffee",
    ],
    "quality": [
        "kupanga cheri kabla ya kupeleka", "daraja la kahawa", "kahawa yangu ilipewa daraja la chini", "jinsi ya kupata daraja bora",
        "nitoe cheri mbaya", "ubora wa kahawa", "cheri chafu kiwandani", "kwa nini daraja liko chini",
        "how to sort cherries before delivery", "my coffee got a low grade", "how to improve coffee quality", "coffee grade",
        "what lowers the grade", "remove bad cherries", "clean cherries for the factory", "grade 1 coffee", "quality ya kahawa",
        "daraja chini", "sorting cherry", "better grade at the factory",
    ],
    "price": [
        "bei ya kahawa leo", "kilo ya kahawa ni pesa ngapi", "mnunuzi ananipa bei ndogo", "bei ya cheri ni ngapi",
        "nimuuzie broker ama chama", "malipo ya chama yatakuja lini", "bei ya dunia ya kahawa", "pesa ya kahawa imechelewa",
        "bei nzuri ya kahawa ni ipi", "chama kinalipa ngapi", "what is the coffee price today", "how much per kilo of cherry",
        "the buyer is offering a low price", "is this a fair price for my coffee", "when will the coop pay",
        "world coffee price", "should i sell to the broker", "price ya kahawa", "broker ananipea 60 bob per kg",
        "bei ngapi", "how much is coffee now", "payment delayed coop",
    ],
    "varieties": [
        "aina ya kahawa isiyoshikwa na ugonjwa", "ruiru 11", "batian", "miche ya kahawa", "nipande aina gani",
        "aina yenye kinga ya kutu", "nataka kupanda upya kahawa", "wapi napata miche", "aina mpya za kahawa",
        "which coffee variety resists disease", "ruiru 11 or batian", "where can i get seedlings", "replanting coffee",
        "disease resistant coffee", "new coffee varieties", "variety gani poa", "miche ya batian", "seedlings za ruiru",
        "best variety for nyeri",
    ],
    "ask_person": [
        "nataka kuongea na afisa ugani", "nipigie simu", "naomba msaada wa mtu", "nataka kuongea na mtu",
        "afisa ugani aje shambani", "niunganishe na chama", "nahitaji mtaalamu", "ongea na mtu",
        "i want to talk to someone", "call me please", "i need the extension officer", "can someone visit my farm",
        "connect me to the coop", "i want a real person", "talk to an expert", "help mtu", "nataka extension officer",
        "officer aje", "speak to a person",
        # where to buy inputs: no vetted source, so a person answers (the cooperative)
        "nanunua dawa wapi", "wapi nanunua mbolea", "where can i buy fertilizer", "where do i buy fungicide",
        "duka la dawa za kahawa liko wapi", "where to get copper spray", "nitapata dawa ya kutu wapi", "shop ya fertilizer iko wapi",
    ],
}

# Farm questions that are NOT in our coffee answer list (other crops, livestock, money, a pest we have no source
# for). They train the "none" class next to the MASSIVE off-topic set, so near misses get "not sure, ask a person"
# instead of a confident wrong coffee answer.
NEAR_NONE = [
    "bei ya maziwa", "bei ya maziwa leo", "milk price today", "bei ya chai", "tea price per kilo", "bei ya mahindi",
    "maize price", "bei ya parachichi", "avocado price", "how do i plant maize", "nipande mahindi lini", "mbegu ya mahindi",
    "my cow is sick", "ng'ombe wangu ni mgonjwa", "ng'ombe hali", "kuku wangu wanakufa", "my chickens are dying",
    "mbuzi mgonjwa", "dawa ya ng'ombe", "majani ya chai yana ugonjwa", "tea leaves turning yellow", "nyanya zinaoza",
    "tomatoes rotting", "maharagwe yana wadudu", "beans have insects", "viazi vina ugonjwa", "potato blight",
    "mkopo wa shamba", "farm loan", "school fees", "karo ya shule", "hospitali iko wapi", "my child has a fever",
    "mtoto ana homa", "wadudu wa antestia", "antestia bugs on my coffee", "antestia kwa kahawa", "kidudu cha antestia",
    "antestia bug control", "mbu wengi nyumbani", "nataka kununua shamba", "bei ya ardhi", "rain forecast tomorrow",
]
