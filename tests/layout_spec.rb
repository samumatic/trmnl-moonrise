# frozen_string_literal: true

require_relative 'support/layout_checks'

# Data that stretches the layout, drawn in every view on TRMNL OG and TRMNL X, landscape and portrait.
# The checks are in tests/support/layout_checks.rb; the places and times are the ones in plugin_spec.rb.
RSpec.describe 'Moonrise & Moonset layout' do
  def fixture(name) = JSON.parse(File.read(File.join(__dir__, 'fixtures', name)))

  let(:berlin) { { 'https://api.open-meteo.com/*' => { json: fixture('open-meteo-berlin.json') } } }
  let(:no_sun) { { 'https://api.open-meteo.com/*' => { status: 500, body: '' } } }
  let(:variables) { { 'trmnl' => { 'user' => { 'time_zone_iana' => 'Europe/Berlin' } } } }

  def berlin_today(**fields) = { now: Time.utc(2026, 10, 20, 8), mocks: berlin, variables:,
                                 custom_fields: { 'lat_lon' => '52.5200,13.4050' }.merge(fields) }

  # A long place name, 12-hour times with AM and PM.
  def long_place_en = berlin_today('language' => 'en', 'location_name' => 'San Cristóbal de las Casas, Chiapas, Mexico')
  # German, whose words are longer: "Abnehmende Sichel", "Monduntergang".
  def long_place_de = berlin_today('language' => 'de', 'location_name' => 'Garmisch-Partenkirchen, Oberbayern, Deutschland')
  # Tromsø without a moonrise: a dash and the longest note, in German.
  def no_moonrise = { now: Time.utc(2026, 4, 4, 10), mocks: no_sun, variables:,
                      custom_fields: { 'lat_lon' => '69.6500,18.9600', 'language' => 'de' } }
  # No location: the empty state.
  def no_place = { now: Time.utc(2026, 10, 20, 8), mocks: { 'https://api.open-meteo.com/*' => { status: 400, body: '' } },
                   variables:, custom_fields: { 'lat_lon' => 'nowhere', 'language' => 'de' } }

  it_behaves_like 'a layout that holds up',
                  'a long place name' => :long_place_en, 'a long German place name' => :long_place_de,
                  'a day without moonrise' => :no_moonrise, 'no location' => :no_place
end
