def categorise(description):
    desc = description.lower()
    
    groceries_kw = [
        'tesco', 'sainsbury', 'asda', 'lidl', 'aldi', 'morrisons', 'coop',
        'marks & spencer', 'm&s', 'waitrose', 'grocery', 'whole foods',
        'supermarket', 'ocado', 'spar'
    ]
    transport_kw = [
        'uber', 'trainline', 'tfl', 'bus', 'tube', 'transport', 'taxi',
        'shell', 'bp', 'esso', 'arriva', 'first bus', 'national express',
        'metro', 'petrol', 'fuel', 'railway', 'bolt'
    ]
    entertainment_kw = [
        'netflix', 'spotify', 'disney', 'steam', 'playstation', 'cinema',
        'pub', 'restaurant', 'bar', 'nandos', 'deliveroo', 'just eat',
        'uber eats', 'starbucks', 'costa', 'cafe', 'gig', 'theatre',
        'hotel', 'event', 'ticketmaster', 'airbnb'
    ]
    bills_kw = [
        'utility', 'electric', 'gas', 'water', 'british gas', 'council tax',
        'rent', 'mortgage', 'broadband', 'bt ', 'virgin media', 'sky ',
        'ee ', 'o2 ', 'vodafone', 'direct debit', 'insurance', 'tax ',
        'subscription', 'mobile', 'cell', 'internet'
    ]
    salary_kw = [
        'salary', 'dividend', 'interest', 'refund', 'payday', 'wages',
        'employer', 'stripe transfer', 'payout', 'monzo transfer'
    ]
    
    if any(w in desc for w in salary_kw):
        return 'Salary'
    if any(w in desc for w in groceries_kw):
        return 'Groceries'
    if any(w in desc for w in entertainment_kw):
        return 'Entertainment'
    if any(w in desc for w in transport_kw):
        return 'Transport'
    if any(w in desc for w in bills_kw):
        return 'Bills'
        
    return 'Other'
