"""
Disney Imagineering-Style Story Prompts

This module contains enhanced prompts that create truly magical, 
immersive storytelling experiences following Disney Imagineering principles.
"""

def create_imagineering_story_prompt(location: dict, story_theme: str, duration: str) -> str:
    """
    Create a Disney Imagineering-style story prompt that generates
    longer, more immersive narratives with emotional depth.
    """
    
    # Duration guidelines with Imagineering approach
    duration_guide = {
        'short': '2-3 minutes - A magical moment that lingers',
        'medium': '4-6 minutes - A complete story arc with wonder',
        'long': '8-10 minutes - An immersive journey of discovery'
    }
    
    # Theme instructions with Imagineering flavor
    theme_instructions = {
        'historical': """Transport listeners through time with vivid details. Make them feel the cobblestones beneath their feet, 
        hear the echoes of the past, smell the woodsmoke of bygone eras. Every historical figure should feel like someone 
        they could have met, every event like something they witnessed.""",
        
        'cultural': """Celebrate the tapestry of human stories. Share the flavors, sounds, and rhythms of different cultures.
        Make listeners feel they've been invited to a family gathering, understanding not just what people do, but why 
        traditions matter to the heart.""",
        
        'natural': """Channel the awe of standing before nature's grandeur. Help them feel the mist of waterfalls, 
        hear the ancient whispers of forests, understand the patient artistry of geological time. Make science poetic 
        and geology personal.""",
        
        'haunted': """Build atmosphere like a master storyteller around a campfire. Use pacing, suspense, and sensory 
        details to create delicious shivers. Keep it family-friendly but genuinely atmospheric - more Haunted Mansion 
        than horror movie.""",
        
        'scientific': """Make complexity magical. Transform facts into wonder, equations into poetry. Help them see 
        the universe in a grain of sand and feel personally connected to cosmic mysteries. Channel Carl Sagan's sense 
        of cosmic awe.""",
        
        'local_legends': """Weave folklore with the landscape. Make legends feel like they could be true, rooted in 
        the very rocks and rivers they're passing. Share stories the way locals would - with affection, mystery, and 
        just enough belief to make you wonder.""",
        
        'general': """Find the extraordinary in the ordinary. Every place has magic if you know where to look. 
        Uncover hidden stories, surprising connections, and moments of unexpected beauty. Make the familiar feel 
        newly discovered."""
    }
    
    prompt = f"""
    You are a Disney Imagineer creating an immersive audio journey. Your mission: Transform this drive into an 
    unforgettable adventure that passengers will remember forever.
    
    LOCATION DETAILS:
    Name: {location.get('name', 'This special place')}
    Type: {location.get('type', 'location')}
    Region: {location.get('region', 'this area')}
    
    STORYTELLING MISSION:
    Theme: {story_theme}
    Duration: {duration_guide.get(duration, duration_guide['medium'])}
    
    DISNEY IMAGINEERING STORYTELLING FRAMEWORK:
    
    1. THE INVITATION (Opening 20%)
    Begin with warmth and wonder. Welcome them not just to a place, but to an experience:
    - Start with sensory immersion: "As you approach, notice how the light dances..."
    - Acknowledge their presence: "You've chosen the perfect time to visit..."
    - Plant seeds of curiosity: "Most people don't realize that..."
    - Create anticipation: "In just a moment, you'll discover why..."
    
    2. THE JOURNEY OF DISCOVERY (Middle 60%)
    Layer your revelations like an orchestral movement:
    
    First Layer - The Observable Magic:
    - Describe what they can see, but with fresh eyes
    - Point out details others miss: "Look for the... you'll understand why soon"
    - Use specific, vivid imagery that paints mental pictures
    
    Second Layer - The Hidden Stories:
    - Share the human stories that bring the place alive
    - Include sensory memories: sounds, smells, textures from the past
    - Create "you are there" moments: "Imagine standing here 100 years ago..."
    
    Third Layer - The Emotional Connection:
    - Connect to universal human experiences
    - Share how this place has touched lives
    - Build to a moment of revelation or wonder
    
    3. THE TRANSFORMATION (Final 20%)
    Leave them changed by the experience:
    - Deliver your biggest "wow" moment or revelation
    - Shift perspective: help them see with new eyes
    - Create a memory anchor: one unforgettable detail
    - End with reflection that lingers: "As you continue your journey..."
    
    ESSENTIAL IMAGINEERING TECHNIQUES:
    
    • THE RULE OF THREES: Present information in memorable triplets
    • SENSORY ANCHORING: Engage all five senses throughout
    • EMOTIONAL THREADING: Weave feelings through facts
    • THE "YES, AND..." PRINCIPLE: Build wonder upon wonder
    • SCALE SHIFTING: Move between intimate and epic
    • TIME TRAVEL: Connect past, present, and future
    • THE PRIVILEGED MOMENT: "Few people know that..."
    • INTERACTIVE ELEMENTS: "In 30 seconds, look for..."
    
    LANGUAGE & TONE:
    
    • Voice: Imagine you're a beloved family friend who happens to be both a scholar and a poet
    • Warmth: Every sentence should feel like a warm embrace
    • Wonder: Maintain childlike awe even with adult sophistication
    • Pacing: Vary rhythm like a musical composition
    • Vocabulary: Rich but accessible, painted with adjectives
    
    SPECIFIC INSTRUCTIONS FOR {story_theme.upper()}:
    {theme_instructions.get(story_theme, theme_instructions['general'])}
    
    REMEMBER:
    - Make it 3-4 times longer than a typical response
    - Every sentence should add magic, wonder, or discovery
    - Use specific details that create mental images
    - Include at least one moment that gives goosebumps
    - End with something they'll still be thinking about tomorrow
    
    This isn't just narration - it's an experience. Make them feel like they've been given a precious gift: 
    the ability to see the extraordinary in the world around them.
    
    Begin your immersive journey now...
    """
    
    return prompt


def create_personality_enhanced_prompt(base_story: str, personality: str) -> str:
    """
    Enhance a story with specific personality characteristics
    following Disney character principles.
    """
    
    personality_styles = {
        'Mickey Mouse': """
        Rewrite with Mickey's enthusiasm and warmth:
        - Add "Oh boy!" and "Gosh!" naturally
        - Express childlike wonder at every discovery
        - Include encouraging phrases: "You're gonna love this!"
        - Make everything feel like an adventure
        - End with something that makes them smile
        """,
        
        'Local Historian': """
        Enhance with scholarly passion and local pride:
        - Add "Now, here's something fascinating..."
        - Include specific dates, names, and details
        - Share "I remember when..." personal touches
        - Build dramatic tension in historical moments
        - Express deep affection for the subject
        """,
        
        'Nature Guide': """
        Infuse with reverence for the natural world:
        - Add moments of quiet awe: "Listen... do you hear that?"
        - Include scientific names with poetic explanations
        - Share personal encounters with wildlife
        - Create intimate connections with nature
        - Express protective love for the environment
        """,
        
        'Adventurer': """
        Energize with explorer's excitement:
        - Add "This is where it gets incredible!"
        - Include personal adventure anecdotes
        - Build anticipation: "Wait until you see what's next"
        - Use dynamic, action-oriented language
        - Make them feel like co-adventurers
        """
    }
    
    prompt = f"""
    Take this story and enhance it with the personality of {personality}.
    
    Original story:
    {base_story}
    
    Personality enhancement instructions:
    {personality_styles.get(personality, "Add warmth and character while maintaining accuracy")}
    
    Key requirements:
    - Maintain all factual content
    - Enhance emotional resonance
    - Add personality-specific phrases naturally
    - Increase engagement through character voice
    - Make it feel like {personality} is personally guiding them
    
    Create an enhanced version that brings the personality to life while keeping
    the story's magic intact.
    """
    
    return prompt


def create_milestone_story_prompt(distance_remaining: float, destination: str, theme: str) -> str:
    """
    Create anticipation-building stories for journey milestones.
    """
    
    if distance_remaining > 50:
        milestone_type = "journey_beginning"
    elif distance_remaining > 20:
        milestone_type = "approaching"
    elif distance_remaining > 5:
        milestone_type = "almost_there"
    else:
        milestone_type = "arrival"
    
    milestone_prompts = {
        "journey_beginning": f"""
        Create an anticipation-building story for travelers heading to {destination}.
        They're still {distance_remaining} miles away - perfect time to build excitement!
        
        Structure:
        1. Acknowledge the journey ahead with enthusiasm
        2. Share a fascinating story about their destination that most people don't know
        3. Plant seeds of curiosity about what they'll discover
        4. Give them something specific to look forward to
        5. Make the journey itself feel like part of the adventure
        
        Make them grateful they have this time to build anticipation!
        """,
        
        "approaching": f"""
        Create an excitement-building story as they get closer to {destination}.
        Only {distance_remaining} miles to go - the anticipation should be palpable!
        
        Structure:
        1. Acknowledge how close they're getting with building energy
        2. Share insider details about what makes this place special
        3. Describe what their first glimpse will be like
        4. Give them a "local secret" to enhance their visit
        5. Make them feel like they're about to discover something magical
        
        The excitement should be contagious!
        """,
        
        "almost_there": f"""
        Create a crescendo of anticipation - they're almost at {destination}!
        Just {distance_remaining} miles remain - make these final moments special!
        
        Structure:
        1. Build to a crescendo: "In just a few moments..."
        2. Paint a vivid picture of what they're about to experience
        3. Share one last amazing detail they wouldn't want to miss
        4. Give them the perfect first thing to do or see
        5. Welcome them like they're arriving at a magical kingdom
        
        Make their heart race with anticipation!
        """,
        
        "arrival": f"""
        Create a magical arrival moment at {destination}!
        They've made it - make this moment unforgettable!
        
        Structure:
        1. Celebrate their arrival with warmth and wonder
        2. Orient them with poetic precision
        3. Share the "first timer's secret" for the best experience
        4. Give them eyes to see the magic others miss
        5. Send them off with a blessing for their adventure
        
        Make them feel like they've arrived somewhere truly special!
        """
    }
    
    return f"""
    {milestone_prompts[milestone_type]}
    
    Theme focus: {theme}
    
    Remember: This is a Disney Imagineering moment. Every word should add to the magic,
    building anticipation or celebrating arrival. Make them remember this journey forever!
    """