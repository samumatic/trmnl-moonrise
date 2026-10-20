# frozen_string_literal: true

# This plugin's tests, run with `trmnlp test` (add `--report report` for a page of every screen it drew).
# Docs: https://github.com/usetrmnl/trmnlp#testing-plugins
# Expected times are from the US Naval Observatory (aa.usno.navy.mil), rounded to the minute like the plugin.
RSpec.describe 'Moonrise & Moonset' do
  def fixture(name) = JSON.parse(File.read(File.join(__dir__, 'fixtures', name)))

  # Open-Meteo's daily sun for a place without its own fixture: local midnight (unix) and seconds of daylight.
  def sun(midnight, daylight, rise: nil, set: nil)
    { 'daily' => { 'time' => [midnight], 'sunrise' => [rise || midnight], 'sunset' => [set || midnight],
                   'daylight_duration' => [daylight] } }
  end

  def zone(name) = { 'trmnl' => { 'user' => { 'time_zone_iana' => name } } }

  # Berlin, 2026-10-20 10:00 local: waxing gibbous, rising in the afternoon, full moon on the 26th.
  let(:now) { Time.utc(2026, 10, 20, 8) }
  let(:mocks) { { 'https://api.open-meteo.com/*' => { json: fixture('open-meteo-berlin.json') } } }
  let(:custom_fields) { { 'lat_lon' => '52.5200,13.4050' } }
  let(:variables) { zone('Europe/Berlin') }

  # Every view on TRMNL's devices, a failing API and every select option, checked for page errors and leaked values.
  it_behaves_like 'a publishable recipe'

  def moon(**inputs) = trmnl.transform(now:, mocks:, custom_fields:, variables:, **inputs).data['moon']

  describe 'Berlin today' do
    it 'computes the phase, rise and set' do
      m = moon
      expect(m.values_at('phase', 'illum', 'age')).to eq(['waxing_gibbous', 66, 9.7])
      expect(m['rise']['t24']).to eq('16:04')
      expect(m['set']['t24']).to eq('00:17')
      expect(m['rise']['t12']).to eq('4:04 PM')
      expect(m['all_day']).to be_nil
    end

    it 'names the next full and new moon in local time' do
      m = moon
      expect(m['full'].values_at('day', 'month', 't24', 'in_days')).to eq([26, 10, '05:12', 6]) # CET after the switch
      expect(m['new'].values_at('day', 'month', 't24')).to eq([9, 11, '08:02'])
      expect(m['next'].map { it['phase'] }).to eq(%w[full last_quarter new first_quarter])
    end

    it 'marks when the moon is up and when it is night' do
      m = moon
      expect(m['up']).to eq([[0.0, 1.2], [66.94, 33.06]])
      expect(m['night'].size).to eq(2)
      expect(m['night'].first.first).to eq(0.0)
      expect(m['now_pct']).to eq(41.67)
    end

    it 'has the coming week, with the full moon on Monday' do
      days = moon['days']
      expect(days.size).to eq(7)
      expect(days.map { it['day'] }).to eq([21, 22, 23, 24, 25, 26, 27])
      expect(days.find { it['phase'] == 'full' }['day']).to eq(26)
    end

    it 'asks Open-Meteo for the sun at the same place and time zone' do
      url = trmnl.transform(now:, mocks:, custom_fields:, variables:).requests.first[:url]
      expect(url).to include('latitude=52.5200', 'longitude=13.4050', 'timezone=Europe%2FBerlin', 'timeformat=unixtime')
    end

    it 'shows the times in German and English' do
      de = trmnl.render(view: 'full', device: 'og_plus', now:, mocks:, variables:,
                        custom_fields: custom_fields.merge('language' => 'de'))
      expect(de.text).to include('Zunehmender Mond', 'Mondaufgang', '16:04', '00:17', 'Mo 26. Okt.', '66 % beleuchtet')
      en = trmnl.render(view: 'full', device: 'og_plus', now:, mocks:, variables:,
                        custom_fields: custom_fields.merge('language' => 'en'))
      expect(en.text).to include('Waxing Gibbous', 'Moonrise', '4:04', '12:17', 'PM', 'Mon, Oct 26', '66% lit')
    end

    it 'follows an explicit time format' do
      screen = trmnl.render(view: 'full', device: 'og_plus', now:, mocks:, variables:,
                            custom_fields: custom_fields.merge('language' => 'en', 'time_format' => '24'))
      expect(screen.text).to include('16:04')
      expect(screen.text).not_to include('PM')
    end
  end

  it 'still draws the moon without the sun when Open-Meteo is down' do
    m = moon(mocks: { 'https://api.open-meteo.com/*' => { status: 500, body: '' } })
    expect(m['rise']['t24']).to eq('16:04')
    expect(m['night']).to be_nil
  end

  it 'asks for a location when it has none' do
    screen = trmnl.render(view: 'full', device: 'og_plus', now:, variables:,
                          mocks: { 'https://api.open-meteo.com/*' => { status: 400, body: '' } },
                          custom_fields: { 'lat_lon' => 'nowhere', 'language' => 'en' })
    expect(screen).to have_no_problems
    expect(screen.text).to include('The moon needs a place')
  end

  # The far north, checked against the USNO: days without a rise, without a set, or with neither.
  describe 'high latitudes' do
    let(:mocks) { { 'https://api.open-meteo.com/*' => { status: 500, body: '' } } }

    {
      'no moonrise (Tromsø)' => ['69.6500,18.9600', Time.utc(2026, 4, 4, 10), nil, :set, 'No moonrise today'],
      'no moonset (Tromsø)' => ['69.6500,18.9600', Time.utc(2026, 1, 24, 10), :rise, nil, 'No moonset today'],
      'the moon up all day (Longyearbyen)' => ['78.2200,15.6500', Time.utc(2026, 12, 24, 10), nil, nil,
                                               'Above the horizon all day'],
      'the moon down all day (Tromsø)' => ['69.6500,18.9600', Time.utc(2026, 7, 22, 10), nil, nil,
                                           'Below the horizon all day']
    }.each do |label, (place, time, rise, set, note)|
      context "with #{label}" do
        let(:now) { time }
        let(:custom_fields) { { 'lat_lon' => place, 'language' => 'en' } }

        it 'reports it' do
          m = moon
          expect(m['rise'].nil?).to eq(rise.nil?)
          expect(m['set'].nil?).to eq(set.nil?)
          expect(m['up']).to eq([]) if note.include?('Below')
          expect(m['up']).to eq([[0.0, 100.0]]) if note.include?('Above')
        end

        %w[full half_horizontal half_vertical quadrant].each do |view|
          it "draws the #{view} view with a dash for the missing time" do
            screen = trmnl.render(view:, device: 'og_plus', now:, mocks:, custom_fields:, variables:)
            expect(screen).to have_no_problems.and(have_no_leaked_text).and(have_no_overlapping_text)
            expect(screen.text).to include('–')
            expect(screen.text).to include(note) if view == 'full'
          end
        end
      end
    end

    it 'shades the whole day as night in the polar night' do
      midnight = Time.utc(2026, 12, 23, 23).to_i
      m = moon(now: Time.utc(2026, 12, 24, 10), custom_fields: { 'lat_lon' => '78.2200,15.6500' },
               mocks: { 'https://api.open-meteo.com/*' => { json: sun(midnight, 0) } })
      expect(m['night']).to eq([[0.0, 100.0]])
    end

    it 'shades nothing in the midnight sun' do
      midnight = Time.utc(2026, 6, 9, 22).to_i
      m = moon(now: Time.utc(2026, 6, 10, 10), custom_fields: { 'lat_lon' => '78.2200,15.6500' },
               mocks: { 'https://api.open-meteo.com/*' => { json: sun(midnight, 86_400) } })
      expect(m['night']).to eq([])
      expect(m['up'].size).to eq(2) # Longyearbyen rises twice that day, 00:16 and 22:02
    end
  end

  context 'in Sydney' do
    let(:custom_fields) { { 'lat_lon' => '-33.8700,151.2100', 'language' => 'en' } }
    let(:variables) { zone('Australia/Sydney') }
    let(:mocks) { { 'https://api.open-meteo.com/*' => { status: 500, body: '' } } }

    it 'lights the waxing moon from the left' do
      expect(moon['disc']).to start_with('M50 0A50 50 0 0 0 50 100')
    end

    it 'shows the coordinates south and east' do
      screen = trmnl.render(view: 'full', device: 'og_plus', now:, mocks:, custom_fields:, variables:)
      expect(screen.text).to include('33.87° S, 151.21° E')
    end
  end
end
